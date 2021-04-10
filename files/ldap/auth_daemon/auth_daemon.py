#A very simple example ldap authentication client
#this client reads the basic auth from the incoming request
#and verifies that the user exist.
from flask import Flask
from flask import request
from flask import Response
from ldap3 import Server, Connection

import json
import base64

ERROR_MSG_FORBIDDEN = "forbidden"
ERROR_MSG_UNAUTHORIZED = "unauthorized"
ERROR_MSG_INVALID_ROLE_SYNTAX = "invalid role syntax"
ERROR_MSG_INTERNAL_ERROR = "internal error"

app = Flask(__name__)

@app.route('/auth')
def auth():
    if request.authorization is None:
        #immediately fail for this example
        return Response(ERROR_MSG_UNAUTHORIZED,status=401)

    user = request.authorization.username
    password = request.authorization.password

    base_dn = request.headers.get('X-Ldap-BaseDn')
    ldap_server = request.headers.get('X-Ldap-URL')

    server = Server(ldap_server)
    conn = Connection(server, request.headers.get('X-Ldap-BindDN'), request.headers.get('X-Ldap-BindPass'), auto_bind=True)
    #search for user
    if not conn.search(base_dn, "(cn={})".format(user)):
        conn.unbind()
        return Response(ERROR_MSG_UNAUTHORIZED,status=401)

    user_result = conn.entries

    #does the user have any roles?
    if not conn.search(base_dn,"(&(roleOccupant=cn={},dc=anzograph,dc=com)(objectClass=organizationalRole))".format(user)):
        conn.unbind()
        return Response(ERROR_MSG_FORBIDDEN,status=403)

    role_results = conn.entries
    groups = []
    if role_results is not None:
        for role in role_results:
            #process the dn to extract the role name
            try:
                role_name = role.entry_dn.split(',')[0].split('=')[1]
                groups.append({'name':role_name})
            except (AttributeError, TypeError, KeyError, IndexError):
                #we could not parse the entry dn from ldap server
                print("Error {} : {}".format(ERROR_MSG_INVALID_ROLE_SYNTAX, role.entry_dn))
                return Response(ERROR_MSG_INTERNAL_ERROR, status=500)

    response_dict = {'name':user, 'member_of': groups}
    user_entry_string = json.dumps(response_dict)
    conn.unbind()

    try:
        user_conn = Connection(server, user_result[0].entry_dn, password, auto_bind=True)
        user_conn.unbind()
    except Exception:
        return Response(ERROR_MSG_UNAUTHORIZED,status=401)
    
    return Response("", status=200, headers={'user-entry': base64.b64encode(user_entry_string.encode('utf-8'))})