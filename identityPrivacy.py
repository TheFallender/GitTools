import os
import subprocess
from configparser import ConfigParser


def modify_git_identity(directory, branch, old_emails, old_names, new_name, new_email):
    # Changing the working directory to the repository directory
    os.chdir(directory)

    # Base correct name and email
    env_filter_script = f'''
        CORRECT_NAME="{new_name}"
        CORRECT_EMAIL="{new_email}"

        export GIT_AUTHOR_DATE="$GIT_AUTHOR_DATE"
        export GIT_COMMITTER_DATE="$GIT_COMMITTER_DATE"
    '''

    # Add the old names rules
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

    # Add the old emails rules
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

    # Run git filter-branch with the constructed env-filter script
    subprocess.run(
        ["git", "filter-branch", "-f", "--env-filter", env_filter_script, branch],
        check=True
    )

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

if __name__ == "__main__":
    # Placeholders for old and new identity details
    OLD_EMAILS, OLD_NAMES, NEW_NAME, NEW_EMAIL, BULK_RUN = read_config("identityPrivacy.ini")

    if BULK_RUN:
        print("Bulk run enabled.")
        dir_of_repos = input("Input the directory where all the repositories are: ")

        for repo in os.listdir(dir_of_repos):
            repo_path = os.path.abspath(os.path.join(dir_of_repos, repo))
            base_cwd = os.getcwd()
            if os.path.isdir(repo_path):
                print(f"Cleaning {repo}")
                os.chdir(repo_path)
                # Get the branches
                branches = subprocess.run(["git", "branch"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True).stdout.split()
                for branch in branches:
                    if branch == '*':
                        continue
                    print(f"Cleaning {repo}'s branch {branch}")
                    modify_git_identity(repo_path, branch, OLD_EMAILS, OLD_NAMES, NEW_NAME, NEW_EMAIL)
            os.chdir(base_cwd)
    else:
        # Requesting user input for repository directory and branch
        repo_dir = input("Please enter the path to the git repository: ")
        branch = input("Please enter the branch you'd like to modify: ")

        print(f"Cleaning repo at {repo_dir} on branch {branch}")
        modify_git_identity(repo_dir, branch, OLD_EMAILS, OLD_NAMES, NEW_NAME, NEW_EMAIL)    