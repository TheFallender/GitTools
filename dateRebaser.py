import subprocess
import os

def run_git_command(command):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    return result.stdout

def main():
    repo_path = input("Enter the path to the repository: ")

    try:
        # Change the active directory to the repository path
        os.chdir(repo_path)
    except FileNotFoundError:
        print(f"Error: Directory {repo_path} not found.")
        return
    except Exception as e:
        print(f"Error: {e}")
        return
    
    # Check if the given directory is a git repository
    try:
        subprocess.run(["git", "status"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    except subprocess.CalledProcessError:
        print("Error: The specified directory is not a git repository.")
        return

    branch = input("Enter the branch name: ")

    # Get the list of commits
    commits = subprocess.run(["git", "rev-list", "--reverse", branch], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True).stdout.split()
    commits.pop(0)

    # Set the GIT_SEQUENCE_EDITOR environment variable to change all "pick" to "edit"
    env = dict(**os.environ, GIT_SEQUENCE_EDITOR="sed -i 's/^pick/edit/'")
    
    # Rebase interactively and edit all commits
    subprocess.run(["git", "rebase", "-i", commits[0] + "^"], check=True, env=env)

    for commit in commits:
        # Get the author date for the commit
        author_date = subprocess.run(["git", "show", "-s", "--format=%aD", commit], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True).stdout.strip()

        # Set the committer date to the author date
        env = dict(**os.environ, GIT_COMMITTER_DATE=author_date)

        # Set the committer date to the author date
        subprocess.run(["git", "commit", "--amend", "--no-edit", "--date", author_date], check=True, env=env)

        # If there are multiple commits, continue the rebase process
        subprocess.run(["git", "rebase", "--continue"], check=True)

    print("Done! All commit dates have been updated.")

if __name__ == "__main__":
    main()