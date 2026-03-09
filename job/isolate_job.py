import re
import subprocess
from pathlib import Path

from .config import Config
from .schema import Status, Submission


class IsolateJob:
    """
    IsolateJob is a class that is used to run the code in a sandbox.
    """

    STDIN_FILE_NAME = "stdin.txt"
    STDOUT_FILE_NAME = "stdout.txt"
    STDERR_FILE_NAME = "stderr.txt"
    METADATA_FILE_NAME = "metadata.txt"

    def __init__(self, submission: Submission):
        self.submission = submission
        self.box_id = submission.id

        # cgroup settings based on submission constraints
        self.cgroups = (
            "--cg"
            if (
                not submission.enable_per_process_and_thread_time_limit
                or not submission.enable_per_process_and_thread_memory_limit
            )
            else ""
        )

    def run_job(self):
        """Process and then clean the created sandbox environment"""
        self.initialize_workdir()

        if self.compile():
            self.run()  # Run the code
            self.verify()
        else:
            self.submission.status = Status.comerr

        self.cleanup()

    def run_command(self, cmd, shell=False):
        """
        Helper to run a shell command securely and safely stringify outputs
        """
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell, text=True
        )
        return result

    def initialize_workdir(self):
        """
        Initialize the sandbox and create all necessary files and folders.
        """
        cmd = f"isolate {self.cgroups} -b {self.box_id} --init"
        result = self.run_command(cmd, shell=True)

        if result.stderr:
            raise Exception(result.stderr)

        self.workdir = Path(result.stdout.strip())

        self.boxdir = self.workdir / "box"
        self.tmpdir = self.workdir / "tmp"

        self.source_file = self.boxdir / self.submission.language.source_file
        self.stdin_file = self.workdir / self.STDIN_FILE_NAME
        self.stdout_file = self.workdir / self.STDOUT_FILE_NAME
        self.stderr_file = self.workdir / self.STDERR_FILE_NAME
        self.metadata_file = self.workdir / self.METADATA_FILE_NAME

        # Initialize input/output files and give necessary ownership
        for f in [
            self.stdin_file,
            self.stdout_file,
            self.stderr_file,
            self.metadata_file,
        ]:
            self.run_command(f"touch {f} && chown $(whoami): {f}", shell=True)

        # Write the user's source code and stdin requirements
        with open(self.source_file, "w") as f:
            f.write(self.submission.source_code)

        with open(self.stdin_file, "w") as f:
            f.write(self.submission.stdin)

    def compile(self):
        # If not compile command is present
        if not self.submission.language.compile_cmd:
            return True

        compile_script = self.boxdir / "compile.sh"
        # Create a tiny runner script to execute the compiler secure parameters
        with open(compile_script, "w") as f:
            compile_cmd = (
                self.submission.language.compile_cmd
                % self.submission.language.source_file
            )
            f.write(compile_cmd)

        compile_output_file = self.workdir / "compile_output.txt"
        self.run_command(
            f"touch {compile_output_file} && chown $(whoami): {compile_output_file}",
            shell=True,
        )

        cg_memeory = (
            f"--mem={Config.MAX_MEMORY_LIMIT}"
            if self.submission.enable_per_process_and_thread_memory_limit
            else f"--cg-mem={Config.MAX_MEMORY_LIMIT}"
        )

        command = f"""isolate {self.cgroups} --silent --box-id={self.box_id} \\
            --meta={self.metadata_file} --stdin=/dev/null --stderr-to-stdout  \\
            --time={Config.MAX_CPU_TIME_LIMIT} --extra-time=0 --wall-time={Config.MAX_WALL_TIME_LIMIT} \\
            --stack={Config.MAX_STACK_LIMIT} --processes={Config.MAX_MAX_PROCESSES_AND_OR_THREADS} \\
            --fsize={Config.MAX_MAX_FILE_SIZE} {cg_memeory} \\
            --env=HOME=/tmp --env=PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \\
            --dir=/etc:noexec --run -- /bin/bash {compile_script.name} > {compile_output_file}
        """

        # Start isolating execution of `compile.sh`
        process = self.run_command(command, shell=True)
        if process.stderr:
            raise Exception(process.stderr)

        # Read compilation output
        with open(compile_output_file, "r") as f:
            self.submission.compile_output = f.read()

        return True if process.returncode == 0 else False

    def run(self):
        run_script = self.boxdir / "run.sh"

        # Create bash script for the actual runner process
        with open(run_script, "w") as f:
            f.write(self.submission.language.run_cmd)

        cg_memeory = (
            f"--mem={self.submission.memory_limit}"
            if self.submission.enable_per_process_and_thread_memory_limit
            else f"--cg-mem={self.submission.memory_limit}"
        )

        command = f"""isolate {self.cgroups} {cg_memeory} --silent --box-id={self.box_id} \\
            --meta={self.metadata_file} --share-net \\
            --time={self.submission.cpu_time_limit} --extra-time={self.submission.cpu_extra_time} \\
            --wall-time={self.submission.wall_time_limit} --stack={self.submission.stack_limit} \\
            --processes={self.submission.max_processes_and_or_threads} \\
            --fsize={self.submission.max_file_size} \\
            --env=HOME=/tmp --env=PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \\
            --dir=/etc:noexec --run -- /bin/bash {run_script.name} \\
            < {self.stdin_file} > {self.stdout_file} 2> {self.stderr_file}
        """

        self.run_command(command, shell=True)

    def verify(self):
        metadata = self.get_metadata()

        self.submission.stdout = self.stdout_file.read_text()
        self.submission.stderr = self.stderr_file.read_text()

        self.submission.time = float(metadata["time"])
        self.submission.wall_time = float(metadata["time-wall"])
        self.submission.memory = int(
            metadata["cg-mem"] if "cg-mem" in metadata else metadata["max-rss"]
        )
        self.submission.exit_code = int(metadata.get("exitcode", "0"))
        self.submission.exit_signal = int(metadata.get("exitsig", "0"))
        self.submission.message = metadata.get("message", "")
        self.submission.status = self.determine_status(
            metadata.get("status", ""), self.submission.exit_signal
        )

    def get_metadata(self) -> dict:
        with open(self.metadata_file, "r", encoding="utf-8") as f:
            content = f.read()

        metadata = {
            data.split(":")[0]: data.split(":")[1] for data in content.splitlines()
        }
        return metadata

    def determine_status(self, status: str, exitsig: int):
        if status == "TO":
            return Status.tle
        elif status == "SG":
            status_code = exitsig
            if status_code == 11:
                return Status.sigsegv
            elif status_code == 25:
                return Status.sigxfsz
            elif status_code == 8:
                return Status.sigfpe
            elif status_code == 6:
                return Status.sigabrt
            elif status_code == 9:
                return Status.mle
            else:
                return Status.other
        elif status == "RE":
            std_err = self.submission.stderr
            if re.match(r"RecursionError: maximum recursion depth exceeded", std_err):
                return Status.rf
            else:
                return Status.nzec
        elif status == "XX":
            message = self.submission.message

            if re.match(r"^execve\(.+\): Exec format error$", message):
                return Status.exeerr
            elif re.match(r"^execve\(.+\): No such file or directory$", message):
                return Status.exeerr
            elif re.match(r"^execve\(.+\): Permission denied$", message):
                return Status.exeerr
            else:
                return Status.boxerr
        elif (
            self.submission.expected_output
            and self.submission.stdout == self.submission.expected_output
        ):
            return Status.acc
        else:
            return Status.wans

    def cleanup(self):
        self.run_command(f"chown -R $(whoami): {self.boxdir}", shell=True)
        self.run_command(f"rm -rf {self.boxdir}/* {self.tmpdir}/*", shell=True)
        for f in [
            self.stdin_file,
            self.stdout_file,
            self.stderr_file,
            self.metadata_file,
        ]:
            self.run_command(f"rm -rf {f}", shell=True)

        self.run_command(
            f"isolate {self.cgroups} -b {self.box_id} --cleanup", shell=True
        )
