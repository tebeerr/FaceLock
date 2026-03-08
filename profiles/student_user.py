# Encrypted face embedding
# User profile configuration — one file per user
import os

class UserProfile:
    def __init__(self, username: str):
        self.username    = username
        self.profile_dir = "profiles"
        self.enc_file    = os.path.join(self.profile_dir, f"{username}.enc")
        self.is_enrolled = os.path.exists(self.enc_file)

    def status(self):
        print(f"\n[PROFILE] User     : {self.username}")
        print(f"[PROFILE] Enrolled : {'Yes ✅' if self.is_enrolled else 'No ❌'}")
        print(f"[PROFILE] File     : {self.enc_file}\n")

# Default user used across all modules
DEFAULT_USER = UserProfile("student_user")