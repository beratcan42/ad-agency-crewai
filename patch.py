import yaml

with open('docker-compose.yml', 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

# Add flowise_data volume
if 'flowise_data' not in data.get('volumes', {}):
    if 'volumes' not in data:
        data['volumes'] = {}
    data['volumes']['flowise_data'] = {'name': 'adagency_flowise_data'}

# Add flowise service
if 'flowise' not in data.get('services', {}):
    if 'services' not in data:
        data['services'] = {}
    data['services']['flowise'] = {
        'image': 'flowiseai/flowise:latest',
        'container_name': 'adagency-flowise',
        'restart': 'unless-stopped',
        'profiles': ['ui'],
        'environment': [
            'PORT=3000',
            'FLOWISE_USERNAME=admin',
            'FLOWISE_PASSWORD=admin',
            'DATABASE_PATH=/root/.flowise',
            'APIKEY_PATH=/root/.flowise',
            'SECRETKEY_PATH=/root/.flowise',
            'LOG_PATH=/root/.flowise/logs'
        ],
        'ports': ['3000:3000'],
        'volumes': ['flowise_data:/root/.flowise'],
        'networks': ['agency_net']
    }

with open('docker-compose.yml', 'w', encoding='utf-8') as f:
    yaml.dump(data, f, default_flow_style=False, sort_keys=False)
