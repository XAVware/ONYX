# import os
# import yaml
# from pathlib import Path

# class Config:
#     """Configuration management for SwiftAI."""
#     def __init__(self):
#         self.config_path = Path.home() / '.swiftai' / 'config.yaml'
#         self.load_config()

#     def load_config(self):
#         if self.config_path.exists():
#             with open(self.config_path) as f:
#                 self.data = yaml.safe_load(f)
#         else:
#             self.data = {
#                 'api_key': os.getenv('ANTHROPIC_API_KEY', ''),
#                 'default_model': "claude-3-7-sonnet-20250219",
#                 'max_tokens': 25000
#             }
#             self.save_config()

#     def save_config(self):
#         self.config_path.parent.mkdir(parents=True, exist_ok=True)
#         with open(self.config_path, 'w') as f:
#             yaml.dump(self.data, f)