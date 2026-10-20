from main import auth_configuration


if __name__ == "__main__":
    status = auth_configuration()
    for name, value in status.items():
        print(f"{name.upper()}={value}")
