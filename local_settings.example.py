ORG_NAME = 'Your Organisation Here'

BASE_URI = 'http://localhost:5000'

SECRET_KEY = 'xxxxxxxxxxxxxxxxxxxxxxxx'

AUTH_METHODS = [
	('email', 'Email'),
	('reddit', 'Reddit')
]

import eos.redditauth.election
ADMINS = [
	#eos.redditauth.election.RedditUser(username='xxxxxxxx')
]

# MongoDB

DB_TYPE = 'mongodb'
DB_URI = 'mongodb://localhost:27017/'
DB_NAME = 'eos'

# PostgreSQL

#DB_TYPE = 'postgresql'
#DB_URI = 'postgresql://'
#DB_NAME = 'eos'

# Email

SMTP_HOST, SMTP_PORT = 'localhost', 25
SMTP_USER, SMTP_PASS = None, None
SMTP_FROM = 'eos@localhost'

# Reddit

REDDIT_OAUTH_CLIENT_ID = 'xxxxxxxxxxxxxx'
REDDIT_OAUTH_CLIENT_SECRET = 'xxxxxxxxxxxxxxxxxxxxxxxxxxx'
REDDIT_USER_AGENT = 'Application Title by /u/Your_Username'
