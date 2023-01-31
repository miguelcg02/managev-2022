# In the server
- sudo mysqldump --databases monitoreodb > /root/db.sql

# In the local pc

Connect from terminal
- ssh -i "C:\Users\Santiago\OneDrive - Universidad EAFIT\Documentos\Universidad\Maestria\Aplicacion\monitoreo.key" root@157.230.209.3

Download the data from the server
- scp -i "C:\Users\Santiago\OneDrive - Universidad EAFIT\Documentos\Universidad\Maestria\Aplicacion\monitoreo.key" root@157.230.209.3:db.sql db.sql

A better aproach is to connect directly with mysql...
Instructions are in presentacion seminario 0