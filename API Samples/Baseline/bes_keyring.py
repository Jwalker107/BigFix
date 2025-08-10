"""bes_keyring - a Module for managing credentials in the keyring"""

import keyring
from dataclasses import dataclass
import getpass

@dataclass 
class bes_keyring:
    system_name: str
    username: str

    def save_credential(self, password):
        keyring.set_password(
            self.system_name,
            self.username,
            password,
        )

    def get_credential(self):
        return keyring.get_password(self.system_name, self.username)

    def prompt_credential(self, prompt="Enter password:", confirm=None):
        """Prompts the user to enter a password
        'prompt' and 'confirm' are the strings presented to the user for prompting
        if 'confirm' is not None, the user is prompted twice and the two passwords must match
          or the prompts are repeated until the same password is typed twice
        """
        password = getpass.getpass(prompt)
        if confirm is not None:
            password2=getpass.getpass(confirm)
            if password == password2:
                return password
            else:
                print("Passwords did not match, retry...")
                return self.prompt_credential(prompt,confirm)
        return password


    def delete_credential(self):
        keyring.delete_password(self.system_name, self.username)