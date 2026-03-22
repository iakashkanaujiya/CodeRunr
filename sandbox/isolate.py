import re
import subprocess
from pathlib import Path

from config import settings
from .schema import SandboxSubmissionStatus, SandboxSubmission


class IsolateCodeSandbox:
    """
    IsolateCodeSandbox is a class that is used to run the code in a sandbox.
    """

    STDIN_FILE_NAME = "stdin.txt"
    STDOUT_FILE_NAME = "stdout.txt"
    STDERR_FILE_NAME = "stderr.txt"
    METADATA_FILE_NAME = "metadata.txt"

    def __init__(self, submission: SandboxSubmission):
        self.submission = submission
        self.box_id = submission.id % 999999

        # cgroup settings based on submission constraints
        self.cgroups = (
            "--cg"
            if (
                not submission.limit_per_process_and_thread_cpu_time_usages
                or not submission.limit_per_process_and_thread_memory_usages
            )
            else ""
        )

    def process_and_execute(self):
        """Process and then clean the created sandbox environment"""
        self.initialize_workdirs()

        if self.compile_code():
            self.run_code()  # Run the code
            self.verify_result()
        else:
            self.submission.status = SandboxSubmissionStatus.comerr

        self.do_cleanup()

    def run_command(self, cmd, shell=False):
        """
        Helper to run a shell command securely and safely stringify outputs
        """
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell, text=True
        )
        return result

    def initialize_workdirs(self):
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

    def compile_code(self):
        # If not compile command is present
        if not self.submission.language.compile_cmd:
            return True

        compile_script = self.boxdir / "compile.sh"
        # Create a tiny runner script to execute the compiler secure parameters
        with open(compile_script, "w") as f:
            compile_cmd = self.submission.language.compile_cmd
            f.write(compile_cmd)

        compile_output_file = self.workdir / "compile_output.txt"
        self.run_command(
            f"touch {compile_output_file} && chown $(whoami): {compile_output_file}",
            shell=True,
        )

        cg_memory = (
            f"--mem={settings.sandbox.MAX_MEMORY_LIMIT}"
            if self.submission.limit_per_process_and_thread_memory_usages
            else f"--cg-mem={settings.sandbox.MAX_MEMORY_LIMIT}"
        )

        command = f"""isolate {self.cgroups} --silent --box-id={self.box_id} \\
            --meta={self.metadata_file} --stdin=/dev/null --stderr-to-stdout  \\
            --time={settings.sandbox.MAX_CPU_TIME_LIMIT} --extra-time=0 --wall-time={settings.sandbox.MAX_WALL_TIME_LIMIT} \\
            --stack={settings.sandbox.MAX_STACK_LIMIT} --processes={settings.sandbox.MAX_MAX_PROCESSES_AND_OR_THREADS} \\
            --fsize={settings.sandbox.MAX_MAX_FILE_SIZE} {cg_memory} \\
            --env=HOME=/tmp --env=PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \\
            --env=NODE_PATH=/usr/local/lib/node_modules \\
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

    def run_code(self):
        run_script = self.boxdir / "run.sh"

        # Create bash script for the actual runner process
        with open(run_script, "w") as f:
            f.write(self.submission.language.run_cmd)

        cg_memory = (
            f"--mem={self.submission.memory_limit}"
            if self.submission.limit_per_process_and_thread_memory_usages
            else f"--cg-mem={self.submission.memory_limit}"
        )

        command = f"""isolate {self.cgroups} {cg_memory} --silent --box-id={self.box_id} \\
            --meta={self.metadata_file} \\
            --time={self.submission.cpu_time_limit} --extra-time={self.submission.cpu_extra_time} \\
            --wall-time={self.submission.wall_time_limit} --stack={self.submission.stack_limit} \\
            --processes={self.submission.max_processes_and_or_threads} \\
            --fsize={self.submission.max_file_size} \\
            --env=HOME=/tmp --env=PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \\
            --env=NODE_PATH=/usr/local/lib/node_modules \\
            --dir=/etc:noexec --run -- /bin/bash {run_script.name} \\
            < {self.stdin_file} > {self.stdout_file} 2> {self.stderr_file}
        """

        self.run_command(command, shell=True)

    def verify_result(self):
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
        self.submission.status = self.extract_status(
            metadata.get("status", ""), self.submission.exit_signal
        )

    def get_metadata(self) -> dict:
        with open(self.metadata_file, "r", encoding="utf-8") as f:
            content = f.read()

        metadata = {}
        for line in content.splitlines():
            key, _, value = line.partition(":")
            metadata[key] = value

        return metadata

    def extract_status(self, status: str, exitsig: int):
        if status == "TO":
            return SandboxSubmissionStatus.tle
        elif status == "SG":
            status_code = exitsig
            if status_code == 11:
                return SandboxSubmissionStatus.sigsegv
            elif status_code == 25:
                return SandboxSubmissionStatus.sigxfsz
            elif status_code == 8:
                return SandboxSubmissionStatus.sigfpe
            elif status_code == 6:
                return SandboxSubmissionStatus.sigabrt
            elif status_code == 9:
                return SandboxSubmissionStatus.mle
            else:
                return SandboxSubmissionStatus.other
        elif status == "RE":
            std_err = self.submission.stderr
            if re.search(r"RecursionError: maximum recursion depth exceeded", std_err):
                return SandboxSubmissionStatus.rf
            else:
                return SandboxSubmissionStatus.nzec
        elif status == "XX":
            message = self.submission.message

            if re.match(r"^execve\(.+\): Exec format error$", message):
                return SandboxSubmissionStatus.exeerr
            elif re.match(r"^execve\(.+\): No such file or directory$", message):
                return SandboxSubmissionStatus.exeerr
            elif re.match(r"^execve\(.+\): Permission denied$", message):
                return SandboxSubmissionStatus.exeerr
            else:
                return SandboxSubmissionStatus.boxerr
        elif not self.submission.expected_output:
            # No expected output to compare — treat as accepted
            return SandboxSubmissionStatus.acc
        elif self.submission.stdout == self.submission.expected_output:
            return SandboxSubmissionStatus.acc
        else:
            return SandboxSubmissionStatus.wans

    def do_cleanup(self):
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
