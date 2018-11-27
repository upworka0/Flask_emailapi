import sys
sys.path.insert(0, '/var/www/html/flaskapp')
import site

site.addsitedir('/home/ubuntu/anaconda3/lib/python3.6/site-packages')
from flaskapp import app as application