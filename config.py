from dotenv import dotenv_values


class Config:
    def __init__(self, config_file=".env"):
        self.config = dotenv_values(config_file)

    def __getattr__(self, item):
        return self.config.get(item)
