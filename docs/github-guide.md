# Guide GitHub + Codex pour grands débutants

Pas besoin de savoir coder. Ce guide vous accompagne pas à pas.

## C'est quoi tout ça ?

- **GitHub** : un site web qui stocke le code du projet. Pensez-y comme un Google Drive pour du code, avec un historique de toutes les modifications.
- **Codex** : un assistant IA intégré à GitHub. Vous lui décrivez ce que vous voulez en français, et il écrit le code pour vous.
- **Repository (repo)** : le dossier du projet sur GitHub. Le nôtre : https://github.com/DorianOuvrard/homeops

## Etape 1 : Créer votre compte GitHub

Si ce n'est pas déjà fait :

1. Allez sur https://github.com
2. Cliquez **Sign up**
3. Suivez les étapes (email, mot de passe, username)
4. Confirmez votre email

## Etape 2 : Accepter l'invitation au projet

Vous avez reçu un email de GitHub intitulé "You've been invited to collaborate".

1. Ouvrez l'email
2. Cliquez sur **"View invitation"**
3. Cliquez sur **"Accept invitation"**

Si vous ne trouvez pas l'email, allez directement sur https://github.com/DorianOuvrard/homeops, GitHub vous proposera d'accepter.

## Etape 3 : Découvrir le projet

Une fois sur https://github.com/DorianOuvrard/homeops :

- La liste des fichiers est au centre
- Le fichier **README.md** s'affiche en bas (c'est la page d'accueil du projet)
- L'onglet **Code** montre les fichiers
- L'onglet **Pull requests** montre les modifications en attente de validation

## Etape 4 : Utiliser Codex pour coder

Codex est votre outil principal. Il code à votre place.

### Ouvrir Codex

1. Depuis le repo https://github.com/DorianOuvrard/homeops
2. Cliquez sur le bouton **"Codex"** (en haut à droite, à côté de "Code")
3. Codex s'ouvre dans une interface de chat

### Demander quelque chose à Codex

Écrivez votre demande **en français**, comme si vous parliez à un collègue. Exemples :

- *"Ajoute un bouton de connexion sur la page d'accueil"*
- *"Corrige le bug qui empêche l'envoi du formulaire"*
- *"Crée une page qui affiche la liste des utilisateurs"*

### Ce que Codex fait ensuite

1. Il lit le code existant du projet
2. Il propose des modifications
3. Il crée automatiquement une **branche** (une copie de travail) et une **Pull Request**
4. Vous pouvez relire ce qu'il a fait avant de valider

### Conseils pour bien utiliser Codex

- **Soyez précis** : "Ajoute un champ email au formulaire d'inscription" marche mieux que "Améliore le formulaire"
- **Découpez** : une demande simple donne de meilleurs résultats qu'une demande complexe
- **Vérifiez** : Codex fait parfois des erreurs. Relisez ce qu'il propose avant de valider.

## Etape 5 : Valider les modifications (Pull Request)

Quand Codex (ou vous) proposez des modifications, ça passe par une **Pull Request (PR)**. C'est une demande de validation avant d'intégrer les changements.

### Relire une PR

1. Allez dans l'onglet **Pull requests**
2. Cliquez sur la PR qui vous intéresse
3. L'onglet **"Files changed"** montre ce qui a été modifié :
   - Les lignes en **vert** sont les ajouts
   - Les lignes en **rouge** sont les suppressions
4. Si tout vous semble bon, cliquez sur **"Merge pull request"** puis **"Confirm merge"**

### Laisser un commentaire

Si quelque chose ne va pas, vous pouvez laisser un commentaire directement sur la PR pour en discuter.

## Vocabulaire express

| Terme | Traduction simple |
|---|---|
| **Repository (repo)** | Le dossier du projet |
| **Branch (branche)** | Une copie de travail pour ne pas casser le projet principal |
| **Commit** | Un point de sauvegarde avec une description |
| **Push** | Envoyer ses modifications sur GitHub |
| **Pull Request (PR)** | Demande de validation avant d'intégrer des changements |
| **Merge** | Valider et intégrer les changements dans le projet |
| **Main** | La branche principale, la version "officielle" du projet |

## En cas de problème

- Ne paniquez pas, on ne peut rien casser définitivement sur GitHub (tout est versionné)
- Demandez de l'aide dans le groupe avant de cliquer sur un bouton dont vous n'êtes pas sûr
- En dernier recours, contactez Dorian
