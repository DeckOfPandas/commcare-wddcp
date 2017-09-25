# commcare-wddcp
*Forked from https://github.com/dimagi/commcare-hq* 
 
This is the GitHub repository for WDDCP, comprising an installation of CommCare HQ forked from [https://github.com/dimagi/commcare-hq](https://github.com/dimagi/commcare-hq). 
 
<br> 

## Workflow and branch structure

Branch **commcare-wddcp:wddcp** is the main branch for WDDCP: Pull Requests should be made into this branch, and releases will be made from here. The branch is protected, so all Pull Requests must be approved by a repository owner.

Branch **commcare-wddcp:dimagi** will be kept up to date with **dimagi:commcare-hq:master** by repository owners. It is locked against Pull Requests, as the only route into it should be by merging from upstream. NB: These merges should all be fast-forward: if they're not then something has gone wrong.

We aim to take updates from upstream (**dimagi/commcare-hq:master**) into **commcare-wddcp:wddcp** as soon as practical, limited by available development time, and conflicts with our changes. Upstream changes should be checked out into a new branch for testing before being incorporated. 

(Branch **commcare-wddcp:master** has been removed to avoid confusion (ha), as it would otherwise be unclear whether commcare-wddcp:master tracked dimagi:master or was the main branch for the WDDCP.)

## Contributions to commcare-wddcp
Contributors to commcare-wddcp should fork the core WDDCP repo (https://github.com/WDDCP/commcare-wddcp), and should make sure their WIP branches are kept up-to-date with branch **commcare-wddcp:wddcp**.

## Quickstart (local)
### Build CommCare HQ
Clone WDDCP-CommCare HQ repo
`git clone git@github.com:WDDCP/commcare-wddcp.git`

Clone WDDCP-FormPlayer repo into CommCare HQ root folder: <br>
`git clone git@github.com:WDDCP/formplayer.git`

In WDDCP-CommCare HQ project root: <br>

Start Vagrant
`vagrant up` 
 - Runs from Vagrantfile and provisions everything
 - Also runs `git submodule update --init --recursive`

Get into new vagrant box: <br>
`vagrant ssh`

Be in the correct folder: <br>
`cd /vagrant` 

Build and set up required services: <br>
`./scripts/docker runserver --bootstrap` 

### Run CommCare HQ server
Inside vagrant machine:<br>
`./scripts/docker runserver`

### Set up django
Start CLI to appropriate docker image: <br>
`./scripts/docker bash` 

Be in the folder where files are: <br>
`cd /mnt/commcare-hq`

Update django models: <br>
`./manage.py makemigrations` then `./manage.py migrate`

**Application should now be available from localhost:8000 (or wherever specified in the `Vagrantfile`)**

### Build FormPlayer
Be in FormPlayer root on vagrant box:
`cd /vagrant/formplayer`

Update submodules: <br>
`git submodule update --init --recursive`

Create a settings file from the sample: <br>
`cp config/application.example.properties config/application.properties`

Install Java APK: <br>
`sudo apt install --yes openjdk-8-jdk`

Install PostgreSQL: <br>
`sudo apt-get install postgresql-9.5 postgresql-client-9.5`

Create a postgres user: <br>
```
sudo -u postgres createuser commcarehq -SDRP
Enter password for new role: <commcarehq>
Enter it again:  <commcarehq>
```
Create a formplayer db under the commcarehq user: <br>
`sudo -u postgres createdb -E UTF-8 -O commcarehq formplayer`

Build with gradlew: <br>
`./gradlew`

Check the management server and server is actually up and accepting connections before going any further: <br>
`curl http://127.0.0.1:8081/`  <br>
{"timestamp":1506094934105,"status":404,"error":"Not Found","message":"/","path":"/"}

`curl http://127.0.0.1:8080` <br>
{"error":"Invalid session id"}

From @lamby:

settings.BASE_ADDRESS in commcare must match what you are accessing the site via in the browser. ie. you cannot have a config.vm.network "forwarded_port", guest: 8000, host: X in your Vagrantfile where X does not match the port mentioned in settings.BASE_ADDRESS in your localsettings. This is due to the commcare Javascript sending an Access-Control-Allow-Origin header of settings.BASE_ADDRESS which violates CORS <https://developer.mozilla.org/en-US/docs/Web/HTTP/Access_control_CORS>__ restrictions in modern browsers.

Be especially aware that changing the port of BASE_ADDRESS in localsettings.py does not actually work. I've yet to discover why but even after re-running the docker initialisation, whilst adding debugging statements to settings.py will happily print the modified value, if you then query settings.BASE_ADDRESS at runtime at all (eg. just dump some print in an already-existing middleware.) it prints an empty string (whut).

Therefore I currently suggest setting guest: 8000, host: 8000. This avoids having to change commcarehq.host=http://localhost:8000 to, say, commcarehq.host=http://localhost:2345 too.
