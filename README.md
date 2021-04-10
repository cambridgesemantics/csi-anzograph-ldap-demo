# csi-anzograph-ldap-demo
# Overview
Example demonstrating how to set up a ldap server and configure AnzoGraph to external authentication.

Utilizes 4 components each deployed in their own containers.
+ NGINX - users will connect and authenticate against this container
+ LDAP auth proxy - NGINX will pass authentication request to this container. 
+ OpenLDAP - a reference OpenLDAP implementation.
+ AnzoGraph

## Download AnzoGraph
Pull the latest nightly image from internal docker repository.
> docker pull cambridgesemantics/anzograph-db:2.3.0-latest

## Building the Required Images

In this example we build the NGINX and LDAP auth proxy images locally.

### Build and tag NGINX
> docker build . -t azg_proxy_nginx

### Build and Tag Auth proxy
> docker build . -f Dockerfile_auth_daemon -t py_auth_daemon

## Create Docker network
We create a dedicated bridge network for our containers so we can resolve them by name. 
> docker network create azg_openldap_integration

## Starting the containers 
The recommended order is 
+ LDAP
+ Auth Proxy
+ AnzoGraph
+ NGINX - must be started last

### Start LDAP server.  
This command will start the reference OpenLDAP server and configure the default domain and admin.

> docker run -p 389:389 -p 636:636 --name azg_openldap --env LDAP_ORGANISATION="AnzoGraph" --env LDAP_DOMAIN="anzograph.com" --env LDAP_ADMIN_PASSWORD="examplepwd" -d --net azg_openldap_integration osixia/openldap:1.4.0

### Add sample LDAP users and roles
We can add additional users by using the ldapadd command. First we copy a file with the user properties to the LDAP server. We then use ldapadd with -f switch to read from the file. example.ldiff creates two users, qauser and devuser, and assigns them to the organizationalRoles, qa and development, respectively. Both users have the password 'test1'

> docker cp files/ldap/example.ldiff azg_openldap:/tmp/example.ldiff

> docker exec azg_openldap ldapadd -D "cn=admin,dc=anzograph,dc=com" -w examplepwd -f /tmp/example.ldiff

### Start the LDAP auth proxy
> docker run -p 5000:5000 -d --net azg_openldap_integration --name example_auth_daemon py_auth_daemon 

### Start AnzoGraph
> docker run -d --name=azg-230-demo --memory=16GB -p 7070:7070 -p 5600:5600 -p 5700:5700  --net azg_openldap_integration cambridgesemantics/anzograph-db:2.3.0-latest

#### Enable ACL and restart
db.ini configures two roles, qa and development.

> docker cp files/db.ini azg-230-demo:/opt/anzograph/config

> docker cp files/settings.conf azg-230-demo:/opt/anzograph/config

> docker exec azg-230-demo /opt/anzograph/bin/azgctl -stop

> docker exec azg-230-demo /opt/anzograph/bin/azgctl -start -init

### Start NGINX
> docker run --name nginx_demo -d -p 8080:80 --net azg_openldap_integration azg_proxy_nginx

## Testing
log into the azg-230-demo container
> docker exec -it azg-230-demo /bin/bash

### Create a graph with qauser
> ./bin/azgi -nossl -h nginx_demo -p 80 -u qauser:test1 -c "create graph \<qaresults\>" -u "qauser:test1"

> ./bin/azgi -nossl -h nginx_demo -p 80 -u qauser:test1 -c "insert data { graph <qaresults> { \<testresult1\> \<elapsed\> 0.001 . }}" -u "qauser:test1"

> ./bin/azgi -nossl -h nginx_demo -p 80 -u qauser:test1 -c "select * from \<qaresults\> where {?s?p?o.}" -raw -u "qauser:test1"

notice the devuser does not have permission to access the qaresults graph
> ./bin/azgi -nossl -h nginx_demo -p 80 -u qauser:test1 -c "select * from \<qaresults\> where {?s?p?o.}" -raw -u "devuser:test1"

### Clean up

## Stop the Containers
> docker stop example_auth_daemon azg_openldap azg-230-demo nginx_demo

You can restart the existing containers by using the docker start command.
> docker start example_auth_daemon azg_openldap azg-230-demo nginx_demo

## Deleting Stopped Containers
> docker rm nginx_demo example_auth_daemon azg_openldap azg-230-demo

## Deleting the Docker network
> docker network rm azg_openldap_integration

## Resources
This demo was adapted from the demo provided in the NGINX documentation
[NGINX Documentation](https://www.nginx.com/blog/nginx-plus-authenticate-users/#:~:text=LDAP%20Server%20Settings,the%20nginx%2Dldap%2Dauth.)