foaf is a small webapp that lets people log in with their Twitter account and
generate a friend-of-a-friend network for a given Twitter user. This can take a
while in the background, but once the data is ready they can download it as a
CSV file.

Under the hood it's a Python Flask application that uses Redis and Supervisor to
manage a set of workers that will go and fetch the data from the Twitter API.

## Develop

You will need Git and Docker to run this app in development:

1. git clone https://github.com/docnow/foaf 
1. cd foaf
1. cp app.cfg.template app.cfg
1. add your Twitter app keys to app.cfg 
1. docker-compose
1. open http://localhost:8000
