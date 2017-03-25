foaf is a small webapp that lets people log with their Twitter credentials and
generate a friend-of-a-friend network for a given Twitter user. This can take a
while, but the user can download the data once it is ready.

## Develop

You will need Git and Docker to run this app in development:

1. git clone https://github.com/docnow/foaf 
1. cd foaf
1. cp app.cfg.template app.cfg
1. add your Twitter app keys to app.cfg 
1. docker-compose
1. open http://localhost:8000
