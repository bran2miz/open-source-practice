# Deploy Discourse on Kubernetes

## Required
Packages
  - awk
  - curl
  - docker
  - kubernetes
  - git

Misc
  - webis Ceph Secret

## Production environment
The discourse production environent contains:
  - 1 Service                 ([prod/discourse-prod.yml](prod/discourse-prod.yml))
  - 1 Deployment              ([prod/discourse-prod.yml](prod/discourse-prod.yml))
  - 2 PersistentVolumeClaims  ([prod/discourse-prod-volumes.yml](prod/discourse-prod-volumes.yml))
  - 1 Secret                  (file not stored in this repository)
  
To deploy the files named basic scripts are provided.

## By Script
To deploy via script all you have to do by hand is fill the information sufficient for your service into `prod/data.yml`. Best create a copy with name `your_service_name.yml` for that. **BE SURE THAT THIS INFORMATION IS NEVER LEAKED TO THE PUBLIC! The SMTP user WILL be highjacked.**

**_NOTE_**: The `developer_emails` should be a comma-separated list of mails, not a yaml-list.

**_CAUTION_**: Not giving all the information may lead to unexpected behavior.

It should look something like:
```
service:
  name: "my_service"    
hostname: "service.domain.io"                 
developer_emails: "first@gmail.com,second@gmail.com"                          
smtp:
  address: "smtp.amazonaws.com"                     
  username: "AKFHAKJSFJBKVAWUHFIA"                    
  password: "KAWFdjwdjahWAHkaFHJwhja"                                            
  port: 587
```

Next manipulate the information in the service configuration `prod/discourse-prod.yml`. Especially you may need to change NodePorts and image description.

After filling the information issue
```
$ cd prod
$ ./setup-discourse -u <DOCKERHUB_USER> -i <DOCKERHUB_IMAGENAME> -f <your_service_name.yml>
```

Everything should be set up now and the container should be running soon.

## By Hand
### Prerequisites
#### Secret
Before the deployment itself can be applied the secret containing SMTP information has to exist.

For the deployment a SMTP server and a Domain Name are needed. The secret stores information about concerning SMTP.
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: discourse-prod-secret
type: Opaque
stringData:
  discourse_developer_emails: "<DEVELOPER_MAIL_1>,<DEVELOPER_MAIL_2>,..."
  discourse_smtp_address: "<SMTP_SERVER>"
  discourse_smtp_user_name: "<SMTP_USERNAME>"
  discourse_smtp_password: "<SMTP_PASSWORD>"
```

Currently AWS SES provides mailing for us. For the information log into the AWS Console, find `Simple Email Service` and under `Domains` check if there is an entry for the domain that the 
Discourse instance is referring to.

If this is the case click `SMTP Settings` on the left. Here you find SMTP server adress and port.

Now only username and passwort are needed to use the SES server. If there already has been an entry for the domain you are working with chances are, that there also is an existing user. Best ask around your team (User + Password are in the `passdb`).

When there is no user yet you can create one at `Create My SMTP Credentials --> Create --> Show User SMTP Credentials`.

These informations are not shown again, so be sure to have them in a safe place.

Lastly developer mails are mails of your choice used for signin in as an admin after startup.
You may now fill in the gaps in the YAML above, save it under `<name_of_your_choice>.yml` and apply it to Kubernetes via 
```
$ kubectl apply -f <name_of_your_choice>.yml
```
Be aware that the name in `discourse-prod.yml` concerning the secret has to match that `<name_of_your_choice>`.

#### Image
The image for the Discourse instance gets created following the tutorial for [discourse_docker](https://github.com/discourse/discourse/blob/master/docs/INSTALL-cloud.md#Install-Discourse).
I will repeat the steps here since there will be some differences.

First clone the related repository.

```
$ sudo -s
# git clone https://github.com/discourse/discourse_docker.git /var/discourse
# cd /var/discourse
```

Next use discourse_dockers launcher to setup the configuration for image creation. Here a file is created at `containers/app.yml`.

```
# ./discourse-setup
```

You will be asked for the following information. You do not actually have to give the information here, since Discourse will pull the information from the [earlier created secret](#secret). You may just supply dummy information.

```
Hostname for your Discourse? [discourse.example.com]: 
Email address for admin account(s)? [me@example.com,you@example.com]: 
SMTP server address? [smtp.example.com]: 
SMTP port? [587]: 
SMTP user name? [user@example.com]: 
SMTP password? [pa$$word]: 
Let's Encrypt account email? (ENTER to skip) [me@example.com]: 
```

When filling these be sure to also overwrite the `SMTP port` with `587` (if your SMTP server listens to that), even when it seems to default to `587`. 
If you don't there might be problems with sending mail, because Discourse (sometimes) uses `25` else. Requests on port `25` cannot reach AWS SES servers from the Webis network (for some reason).

**_IMPORTANT_**: If there occurs any error (which is very likely already at the domain check) you have to edit `containers/app.yml` yourself. If so, enter the information which is mentioned [above](https://github.com/tira-io/tira/edit/master/tira-discourse-deployment/README.md#L68) at the position you find it in the file.
When you entered them restart the building process via `./launcher rebuild app`. Do not skip this!

So after the setup edit the file at `containers/app.yml` as follows:

  - rename the file to `<your_service_name>.yml`
  - make sure the information at `env`, which got asked for in the setup was entered correctly. Else please correct it.
  - at `hooks.after_code.exec.cmd` enter another listentry for Disraptor
    - `- git clone https://github.com/disraptor/disraptor.git`
 
Everything is ready for image creation now. So leave the previously edited file and start the image and container creation.

```
$ docker stop app && docker rm app
# ./launcher rebuild <your_service_name>
```

An image will be created and a corresponding container will also be started. This might take a while.

You can now retag the image by your choice and push it to your docker registry.

```
$ docker tag local_discourse/<your_service_name>:latest <USER>/<NAME>:<TAG>
$ docker push <USER>/<NAME>:<TAG>
```

You may need to change the image information in the Deployment configuration at `spec.template.spec.containers.image` accordingly.

#### Ceph
To mount certain boot-specific resources into the container we use a [CephFSVolumeSource](https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.18/#cephfsvolumesource-v1-core).
Be sure CephFS mounted with the correct permissions (webisstud or webis). For information how to mount ceph follow [this](https://git.webis.de/code-generic/code-admin-knowledgebase/blob/master/services/ceph/cephfs-usage.md).

Copy the corresponding files by:

```
$ cd ~/discourse-k8s-deploy
$ cp /var/discourse/shared/standalone /mnt/ceph/storage/data-in-production/disraptor/boot/resource
```

Also the setup file from this repository is needed to setup permissions for the files.

```
$ cp prod/setup /mnt/ceph/storage/data-in-production/disraptor/boot/setup
```

Now everything is perfectly set up to deploy your Discourse production instance.

### Deployment
Complete deployment will be done by:

```
$ prod/k8s-deploy-discourse-prod.sh
```

### Undeploying
Remove the deployment by:

```
$ prod/k8s-undeploy-discourse-prod.sh
```

Your volumes will not be removed by this. Only `Service` and `Deployment` are defined in `prod/discourse-prod.yml` and therefore only these will be deleted here. This secures persistent data to be persistent across deploys.

**_If you really want to remove them use (this will remove all your Discourse-related data)_**:

```
$ kubectl delete -f prod/discourse-prod-volumes.yml
```

#### Updating
After having done all the manual steps above one does not have to repeat them for updating the Discourse instance.
This can be done via script, issueing:
```
# prod/update-discourse.sh -u <DOCKERHUB_USER> -i <DOCKERHUB_IMAGENAME> -t <TAG> -s <SERVICE_NAME>
```
which will rebuild the image for the given service with given Dockerhub imagename and tag.
It will proceed to push the image to Dockerhub once with the tag you gave and once tagged as latest.
The script will fail if the given tag already exists for the image so you don't override images.

## Development environment

The discourse development environent contains:
  - 1 Service                 ([dev/discourse-dev.yml](dev/discourse-dev.yml))
  - 1 Deployment              ([dev/discourse-dev.yml](dev/discourse-dev.yml))
  - 1 PersistentVolumeClaim   ([dev/persistent-volume.yml](dev/persistent-volume.yml))
  
To deploy the files named basic scripts are provided.

### Deploying

First, to prevent collision with other development instances you have to choose a port `<PORT>` for your instance. Or rather 2. One for http and one for the mailcatcher. Do this by editing the Service in ([dev/discourse-dev.yml](dev/discourse-dev.yml)) at spec.ports accordingly (from 3080X to something you choose).
If the nodePorts you choose are already occupied in the cluster the pod won't be able to start up and you have to choose others.

After that deployment of the development environment is as simple as running `./k8s-deploy-discourse-dev.sh -n <NAMESPACE>`, where `<NAMESPACE>` refers to the namespace you want to deploy in.
All the heavy lifting is then done by the configs and the commands executed there.
After the pod started, you have the possibility to read through the (pretty short) logs produces while starting up by using `./logs.sh -n <NAMESPACE>`. This is also very handy for unexpected issues.

Right after startup a admin account for the Discourse instance needs to be created. Because this instance is in production mode, and emails can therefore not be sent this has to be done manually with the `create-admin` script via `./create-admin.sh -n <NAMESPACE>`.

Now the instance is visitable on any betaweb machine at port `30804`. Be aware that `betawebXXX.medien.uni-weimar.de:30804` does not work, but only `betawebXXX:30804` does.

### Undeploying

This works the same way, as for the production instance basically.
Remove the deployment by:

```
$ prod/k8s-undeploy-discourse-dev.sh
```

Your volumes will not be removed by this. Only `Service` and `Deployment` are defined in `prod/discourse-prod.yml` and therefore only these will be deleted here. This secures persistent data to be persistent across deploys.