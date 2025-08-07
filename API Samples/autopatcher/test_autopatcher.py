# This script is to automate testing of the autopatchy.py script by keeping collections of command-line arguments.

import autopatcher
import sys, os


def get_script_path():
    """Returns the directory of the running script.  Useful for defaulting a configuration file path to match the script itself."""
    if getattr(sys, "frozen", False):
        # If the application is run as a bundle (precompiled binary), the PyInstaller bootloader
        # # extends the sys module by a flag frozen=True and sets the app
        # # path into variable _MEIPASS'.
        # print("Using frozen config")
        return os.path.dirname(os.path.abspath(sys.executable))
    else:
        return os.path.dirname(os.path.abspath(__file__))


def main():
    """Main function to run the autopatcher script."""
    ### Each potential command-line argument is listed below.  Set the 'if True:' condition to True to run that command.

    if False:
        # Generate a baseline preview only
        autopatcher.main(
            [
                "--query",
                os.path.join(get_script_path(), "componentgroup1.txt"),
                "--preview",
            ]
        )

    if False:
        # Create a baseline and create an action preview only targeting by CustomRelevance
        autopatcher.main(
            [
                "--query",
                os.path.join(get_script_path(), "componentgroup1.txt"),
                "--preview-action",
                "--target-computer-query",
                os.path.join(get_script_path(), "computers_query.txt"),
            ]
        )

    if False:
        # Create a baseline and create an action preview only targeting by CustomRelevance
        autopatcher.main(
            [
                "--query",
                os.path.join(get_script_path(), "componentgroup1.txt"),
                "--preview-action",
                "--target-computer-query",
                os.path.join(get_script_path(), "computers_query.txt"),
            ]
        )
    if False:
        # Create a baseline and create an action preview only targeting by ComputerName
        autopatcher.main(
            [
                "--query",
                os.path.join(get_script_path(), "componentgroup1.txt"),
                "--preview-action",
                "--target-computer-names",
                "Computer1",
                "Computer2",
                "Computer3",
            ]
        )

    if False:
        # Create a baseline and create an action preview only targeting by ComputerID
        autopatcher.main(
            [
                "--query",
                os.path.join(get_script_path(), "componentgroup1.txt"),
                "--preview-action",
                "--target-computer-ids",
                "1080035267",
            ]
        )

    if True:
        # Create a baseline and create an action targeting by ComputerID
        autopatcher.main(
            [
                "--query",
                os.path.join(get_script_path(), "componentgroup1.txt"),
                "--preview-action",
                "--target-computer-ids",
                "1080035267",
            ]
        )


if __name__ == "__main__":
    main()
