from flask import Flask

app = Flask(__name__)

@app.route('/')
def ciao():
    return '<h1>Ciao!</h1>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6006, debug=True)