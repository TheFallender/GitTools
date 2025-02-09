import os
import re
import subprocess
from configparser import ConfigParser


# Get the output from the command
def get_output(cmd, cwd=None):
    if cwd is None:
        cwd = os.getcwd()

    result = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=False,
        check=True
    )
    return result.stdout


# Modify the Git Identity
def modify_git_identity(directory,
                        branch_or_all,
                        old_emails,
                        old_names,
                        new_name,
                        new_email):
    # Change to the repository's directory
    os.chdir(directory)

    # Base correct name and email, preserving commit timestamps
    env_filter_script = f'''
        CORRECT_NAME="{new_name}"
        CORRECT_EMAIL="{new_email}"

        # Preserve commit timestamps
        export GIT_AUTHOR_DATE="$GIT_AUTHOR_DATE"
        export GIT_COMMITTER_DATE="$GIT_COMMITTER_DATE"
    '''

    # Add old names rules
    for old_name in old_names:
        env_filter_script += f'''
        if [ "$GIT_COMMITTER_NAME" = "{old_name}" ]; then
            export GIT_COMMITTER_NAME="$CORRECT_NAME"
            export GIT_COMMITTER_EMAIL="$CORRECT_EMAIL"
        fi
        if [ "$GIT_AUTHOR_NAME" = "{old_name}" ]; then
            export GIT_AUTHOR_NAME="$CORRECT_NAME"
            export GIT_AUTHOR_EMAIL="$CORRECT_EMAIL"
        fi
        '''

    # Add old emails rules
    for old_email in old_emails:
        env_filter_script += f'''
        if [ "$GIT_COMMITTER_EMAIL" = "{old_email}" ]; then
            export GIT_COMMITTER_NAME="$CORRECT_NAME"
            export GIT_COMMITTER_EMAIL="$CORRECT_EMAIL"
        fi
        if [ "$GIT_AUTHOR_EMAIL" = "{old_email}" ]; then
            export GIT_AUTHOR_NAME="$CORRECT_NAME"
            export GIT_AUTHOR_EMAIL="$CORRECT_EMAIL"
        fi
        '''

    # Squelch git filter-branch warning
    os.environ["FILTER_BRANCH_SQUELCH_WARNING"] = "1"

    # Determine command based on whether we're updating a specific branch or all refs
    cmd = [
        "git",
        "filter-branch",
        "-f",
        "--env-filter",
        env_filter_script
    ]
    if branch_or_all == "--all":
        cmd += ["--", "--all"]
    else:
        cmd += [branch_or_all]

    # Using subprocess.Popen to stream the progress output
    with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    ) as proc:
        for line in proc.stdout:
            print(line.rstrip())

        proc.wait()
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, cmd)


# Read from the config file
def read_config(config_path):
    config = ConfigParser()
    config.read(config_path)
    
    identity = config["Identity"]
    old_emails = [email.strip() for email in identity["OldEmails"].split(",")]
    old_names = [name.strip() for name in identity["OldNames"].split(",")]
    new_name = identity["NewName"]
    new_email = identity["NewEmail"]

    modes = config["Modes"]
    bulk_run = modes.getboolean("Bulk")
    
    return old_emails, old_names, new_name, new_email, bulk_run


# Local branch check
def branch_exists_local(branch_name):
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", branch_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return result.returncode == 0


# Get branches up to date from remote
def get_branches_up_to_date():
    # Fetch all the branches
    get_output(["git", "fetch", "--all"])

    # See the remote branches
    remote_branches = get_output(["git", "branch", "-r"]).splitlines()

    # Regex to remove ANSI escape sequences
    ansi_escape = re.compile(r'\x1B\[[0-9;]*[a-zA-Z]')

    for branch in remote_branches:
        # Remove ANSI escape sequences and strip whitespace
        branch = ansi_escape.sub("", branch).strip()

        # Skip lines containing '->'
        if "->" in branch:
            continue

        if "/" not in branch:
            print(f"Skipping branch '{branch}' as it doesn't contain a remote name.")
            continue

        # Get the local branch name by splitting on '/', taking everything after
        # the first slash
        parts = branch.split("/", 1)
        if len(parts) < 2 or not parts[1]:
            print(f"Skipping branch '{branch}' due to invalid naming.")
            continue

        remote_name = parts[0]
        local_branch = parts[1]

        # Check if the branch already exists locally
        if branch_exists_local(local_branch):
            print(f"Local branch '{local_branch}' already exists, do a pull.")
            get_output(["git", "checkout", local_branch])
            get_output(["git", "pull", remote_name, local_branch])
            continue

        # Create tracking branch using the local branch name and full remote branch
        try:
            print(f"Tracking branch '{local_branch}' for remote '{branch}'")
            get_output(["git", "branch", "--track", local_branch, branch])
            get_output(["git", "checkout", local_branch])
            get_output(["git", "pull", remote_name, local_branch])
        except subprocess.CalledProcessError as e:
            print(f"Failed to track branch '{local_branch}': {e}")
                  
if __name__ == "__main__":
    # Placeholders for old and new identity details
    OLD_EMAILS, OLD_NAMES, NEW_NAME, NEW_EMAIL, BULK_RUN = read_config("identityPrivacy.ini")

    if BULK_RUN:
        print("Bulk run enabled.")
        # dir_of_repos = input("Input the directory where all the repositories are: ")
        dir_of_repos = 'gh'

        for repo in os.listdir(dir_of_repos):
            repo_path = os.path.abspath(os.path.join(dir_of_repos, repo))
            base_cwd = os.getcwd()
            if os.path.isdir(repo_path):
                print(f"Cleaning {repo}")
                os.chdir(repo_path)
                
                # Get the remote branches
                get_branches_up_to_date()

                # Get the branches
                branches = subprocess.run(["git", "branch"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True).stdout.split()

                modify_git_identity(repo_path, "--all", OLD_EMAILS, OLD_NAMES, NEW_NAME, NEW_EMAIL)    
            os.chdir(base_cwd)
    else:
        # Requesting user input for repository directory and branch
        repo_dir = input("Please enter the path to the git repository: ")
        branch = input("Please enter the branch you'd like to modify: ")

        print(f"Cleaning repo at {repo_dir} on branch {branch}")
        modify_git_identity(repo_dir, branch, OLD_EMAILS, OLD_NAMES, NEW_NAME, NEW_EMAIL)    