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
    '''

    # Add the old names rules
    for old_name in old_names:
        env_filter_script += f'''
        if [ "$GIT_COMMITTER_NAME" = "{old_name}" ]
        then
            export GIT_COMMITTER_NAME="$CORRECT_NAME"
            export GIT_COMMITTER_EMAIL="$CORRECT_EMAIL"
        fi
        if [ "$GIT_AUTHOR_NAME" = "{old_name}" ]
        then
            export GIT_AUTHOR_NAME="$CORRECT_NAME"
            export GIT_AUTHOR_EMAIL="$CORRECT_EMAIL"
        fi
        '''

    # Add the old emails rules
    for old_email in old_emails:
        env_filter_script += f'''
        if [ "$GIT_COMMITTER_EMAIL" = "{old_email}" ]
        then
            export GIT_COMMITTER_NAME="$CORRECT_NAME"
            export GIT_COMMITTER_EMAIL="$CORRECT_EMAIL"
        fi
        if [ "$GIT_AUTHOR_EMAIL" = "{old_email}" ]
        then
            export GIT_AUTHOR_NAME="$CORRECT_NAME"
            export GIT_AUTHOR_EMAIL="$CORRECT_EMAIL"
        fi
        '''
    
    # Setting the environment variable to squelch warning
    os.environ["FILTER_BRANCH_SQUELCH_WARNING"] = "1"

    # Run git filter-branch with the constructed env-filter script
    subprocess.run(["git", "filter-branch", "-f", "--env-filter", env_filter_script, branch])

# Read from the config file
def read_config(config_path):
    config = ConfigParser()
    config.read(config_path)
    
    identity = config["Identity"]
    
    old_emails = [email.strip() for email in identity["OldEmails"].split(",")]
    old_names = [name.strip() for name in identity["OldNames"].split(",")]
    new_name = identity["NewName"]
    new_email = identity["NewEmail"]
    
    return old_emails, old_names, new_name, new_email

if __name__ == "__main__":
    # Requesting user input for repository directory and branch
    repo_dir = input("Please enter the path to the git repository: ")
    branch = input("Please enter the branch you'd like to modify: ")

    # Placeholders for old and new identity details
    OLD_EMAILS, OLD_NAMES, NEW_NAME, NEW_EMAIL = read_config("identityPrivacy.ini")

    print(f"Cleaning repo at {repo_dir} on branch {branch}")
    modify_git_identity(repo_dir, branch, OLD_EMAILS, OLD_NAMES, NEW_NAME, NEW_EMAIL)
