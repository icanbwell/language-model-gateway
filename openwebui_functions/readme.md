# Pipes for installing and running in OpenWebUI

## OpenWebUI Pipes
https://docs.openwebui.com/features/plugin/functions/pipe/

## Instructions to add pipe to OpenWebUI on local machine
- Run `make down; make up-open-webui-auth` to start OpenWebUI with authenticatio
- Login with admin/password to openwebui 
- Now run `make set-admin-user-role` to set the admin role for this new user
- Reload the OpenWebUI page in your browser
- Click top right icon and select Admin Panel
- Click Functions tab
- Click Import Functions (don’t click + to add a new function)
- Select the language_model_gateway_pipe.json file in the openwebui_functions folder in language_model_gateway 
- This contains the content of openai.py in a json string so update that if you change openai.py
- After the function has been loaded, make sure to click the toggle next to it to turn it on
- Now go back to the main UI
- There should be new models in the model dropdown