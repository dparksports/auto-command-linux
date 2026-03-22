
```sh
sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup
sudo sed -i 's|http://security.ubuntu.com/ubuntu/|https://mirrors.wikimedia.org/ubuntu/|g' /etc/apt/sources.list
sudo sed -i 's|http://us.archive.ubuntu.com/ubuntu/|https://mirrors.wikimedia.org/ubuntu/|g' /etc/apt/sources.list
```
