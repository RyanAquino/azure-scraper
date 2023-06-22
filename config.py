from dotenv import dotenv_values


class Config:
    def __init__(self, config_file=".env"):
        self.config = dotenv_values(config_file)

    def __getattr__(self, item):
        value = self.config.get(item)
        if value.isdigit():
            value = int(value)
        return value
