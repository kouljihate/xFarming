from app import create_app
from app.database import init_db

app = create_app()

if __name__ == '__main__':
    try:
        with app.app_context():
            init_db()
        app.run(debug=True, port=5001)
    except Exception as e:
        # print(e)
        app.logger.error(e)
    except KeyboardInterrupt:
        # print("SFarming stopped by user")
        app.logger.error("SFarming stopped by user")
        

    