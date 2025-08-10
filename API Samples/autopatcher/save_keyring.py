"""Prompt to save a credential to the system keyring"""

import keyring
import getpass


def prompt_credential(prompt="Enter password:", confirm=None):
    """Prompts the user to enter a password
    'prompt' and 'confirm' are the strings presented to the user for prompting
    if 'confirm' is not None, the user is prompted twice and the two passwords must match
      or the prompts are repeated until the same password is typed twice
    """
    password = getpass.getpass(prompt)
    if confirm is not None:
        password2 = getpass.getpass(confirm)
        if password == password2:
            return password
        else:
            print("Passwords did not match, retry...")
            return prompt_credential(prompt, confirm)
    return password


def main():
    """Main function to demonstrate the bes_keyring functionality"""

    system_name: str = input("Enter the system name for the keyring: ")
    username: str = input("Enter the username for the keyring: ")
    password: str = prompt_credential(
        "Enter password for the keyring: ", confirm="Confirm password: "
    )

    keyring.set_password(
        system_name,
        username,
        password,
    )
    print("Credential saved to keyring.")
    # keyring.get_password(system_name, username)
    # keyring.delete_password(system_name, username)


if __name__ == "__main__":
    main()
