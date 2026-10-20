from database import close_pool, test_connection


if __name__ == "__main__":
    try:
        test_connection()
    except Exception as exc:
        # Never print the connection string or exception text, which can
        # include driver-rendered connection details.
        print(f"DATABASE_CONNECTION_FAILED: {type(exc).__name__}")
        close_pool()
        raise SystemExit(1)
    finally:
        close_pool()
    print("DATABASE_CONNECTION_OK")
