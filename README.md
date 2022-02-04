# Satosa-blockchainlab2SPID

- derivato da [Satosa-Saml2SPID](https://github.com/italia/Satosa-Saml2Spid)


la cartella [project](./project) è la copia della cartella [example](./example)

# Scegliere Nomi di Dominio

per prima cosa bisogna scegliere due nomi di dominio, nel nostro caso:

-  spid.blockchainlab.it : riferito al servizio proxy basasto su satosa;
-  discovery.blockchainlab.it : riferito al servizio discovery e ai contenuti statici. 

Aggiornare i seguenti file con i nomi di dominio scelti e le informazioni personali richieste (Es. nome, contatti, p. iva...):

- [project/proxy_conf.yaml](./project/proxy_conf.yaml)
- [project/plugins/backends/saml2_backend.yaml](./project/plugins/backends/saml2_backend.yaml)
- [project/plugins/backends/spidsaml2_backend.yaml](./project/plugins/backends/spidsaml2_backend.yaml)
- [project/plugins/frontends/saml2_frontend.yaml](./project/plugins/frontends/saml2_frontend.yaml)

- [init-letsencrypt.sh](./init-letsencrypt.sh)
- [docker/gateway/satosa.conf](./docker/gateway/satosa.conf)

> NOTA per il file satosa.conf: <br>
> il nome della cartella in cui let's encrypt genera i certitificati per i due domini è il nome del primo dominio indicato nel file init-letsencrypt.sh, per entrambi i domini.


# Modificare i templates delle pagine statiche

modificare i seguenti file html:

- [project/static/disco.html](./project/static/disco.html)
- [project/static/error_page.html](./project/static/error_page.html)
- [project/templates/spid_base.html](./project/templates/spid_base.html)


# Aggiungere IdP 

- scaricare i metadata dell' Identity Provider che si vuole aggiungere nella cartella project/metadata/idp. Es.
    - [Validator di test](https://demo.spid.gov.it/validator/metadata.xml)
    - [ambiente Demo](https://demo.spid.gov.it/metadata.xml)

    ```
    wget https://demo.spid.gov.it/validator/metadata.xml -O Satosa-blockchainlab2SPID/project/metadata/idp/nome_idp.xml
    ```

- Aggiungere l' EntityID del Identity Provider al file [project/plugins/microservices/target_based_routing.yaml](./project/plugins/microservices/target_based_routing.yaml) seguendo lo stesso formato degli altri IdP già presenti.

- Aggiungere l'IdP al bottone 'Entra con SPID', aggiungendone l'entityID nel file [project/static/spid/spid-idps.js](./project/static/spid/spid-idps.js) seguendo lo stesso formato degli altri IdP già presenti.

# Aggiungere SP

- scaricare i metadata del Service Provider che si vuole aggiungere nella cartella project/metadata/sp

    ```
    wget https://con-cert.eu.auth0.com/samlp/metadata?connection=proxy -O Satosa-blockchainlab2SPID/project/metadata/sp/my-sp.xml
    ```

# DOCKER-COMPOSE

## - Modificare docker-compose.yaml

- inserire le informazioni necessarie per generare i certificati per il docker spid-certs;

- aggiungere il docker di nginx
    ```
    satosa-nginx:
        image: nginx:1.15-alpine
        container_name: satosa-nginx
        restart: unless-stopped
        volumes:
        - ./docker/gateway/satosa.conf:/etc/nginx/conf.d/default.conf
        - satosa-saml2saml_statics:/satosa_statics
        - ./docker/gateway/log:/var/log/nginx
        - ./docker/certbot/conf:/etc/letsencrypt
        - ./docker/certbot/www:/var/www/certbot
        ports:
        - "80:80"
        - "443:443"
        command: "/bin/sh -c 'while :; do sleep 6h & wait $${!}; nginx -s reload; done & nginx -g \"daemon off;\"'"
        networks:
        - satosa
    ```
- aggiungere il docker di certbot per generare i certificati SSL per let's encrypt
    ```
    certbot:
        image: certbot/certbot
        container_name: certbot
        restart: unless-stopped
        volumes:
        - ./docker/certbot/conf:/etc/letsencrypt
        - ./docker/certbot/www:/var/www/certbot
        entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
    ```

## - Eseguire i comandi

````
apt install jq
pip install docker-compose
````

Creare i volumi
````
docker volume create --name=satosa-saml2saml_certs
docker volume create --name=satosa-saml2saml_conf
docker volume create --name=satosa-saml2saml_statics
docker volume create --name=satosa-saml2saml_logs
````

Where the data are
`docker volume ls`

Copiare i file nei volumi di destinazione

````
cp project/pki/*pem `docker volume inspect satosa-saml2saml_certs | jq .[0].Mountpoint | sed 's/"//g'`
cp -R project/* `docker volume inspect satosa-saml2saml_conf | jq .[0].Mountpoint | sed 's/"//g'`
cp -R project/static/* `docker volume inspect satosa-saml2saml_statics | jq .[0].Mountpoint | sed 's/"//g'`
````

avviare docker-compose
````
docker-compose up
````

See [mongo readme](./mongo/README.md) to have some example of demo data.


# Metadata Proxy

- Metadata frontend (da fornire al SP)

        https://spid.blockchainlab.it/Saml2IDP/metadata
- Metadata backend (da fornire all' IdP)

        https://spid.blockchainlab.it/spidSaml2/metadata
# Auth0

- Creare una nuova connessione in Authentication>Enterprise>SAML.
    
    **Sign in URL**:
            
        https://spid.blockchainlab.it/Saml2/sso/post

    o cercare _md:SingleSignOnService_ nei metadata del frontend;

    **X509 Signing Certificate**:

    Ottenerlo dai metadata del frontend.

# Aggiornare Signing Keys per la connessione appena creata
Ottenere Acceess Token per l' applicazione 'API Exploreer Application'.

````
curl --request POST \
  --url https://con-cert.eu.auth0.com/oauth/token \
  --header 'content-type: application/json' \
  --data '{"client_id":"<client_id>","client_secret":"<client_secreet>","audience":"https://con-cert.eu.auth0.com/api/v2/","grant_type":"client_credentials"}'
````
utilizzabile poi con client come Postman o da command lin econ curl:
````
curl --request GET \
  --url http://path_to_your_api/ \
  --header 'authorization: Bearer <access_token>
````

## API da utilizzare:

- GET https://con-cert.eu.auth0.com/api/v2/connections

    restituisce tutte le informazioni di tutte le connessioni create

- GET https://con-cert.eu.auth0.com/api/v2/connections/_connection_id_

    restituisce tutte le informazioni di quella specifica connessione

- PATCH https://con-cert.eu.auth0.com/api/v2/connections/_connection_id_

    sovrascrive le informazioni della connessione con quelle inserite nel body della richiesta. qui vanno inserite le chiavi.


# Creare mapping attributio nella connessione

````
{
  "sn": "urn:oid:2.5.4.4",
  "name": "Name",
  "email": "urn:oid:1.2.840.113549.1.9.1.1",
  "spid_code": "spidCode",
  "given_name": "urn:oid:2.5.4.42",
  "family_name": "familyName",
  "display_name": "urn:oid:2.16.840.1.113730.3.1.241",
  "eduPersonTargetedID": "urn:oid:1.3.6.1.4.1.5923.1.1.1.10"
}
````

# Abilitare connessione in un'Applicazione e testarla
- prima di testare controllare che l' url del sito di origine sia inserito tra i siti autorizzati all' interno dell' Applicazione dentro la quale eè stata abilitata la connessione