Vagrant.configure(2) do |config|
  config.vm.box = "ubuntu/xenial64"
  config.vm.box_version = "20170830.1.1"

# BASH THINGS

  # The more the better; this feels like minimum-viable
  config.vm.provider "virtualbox" do |v|
    v.memory = 4096
    v.cpus = 2
  end

  config.vm.network "forwarded_port", guest: 8000, host: 2345

  config.vm.provision "shell", inline: <<-SHELL
    sudo apt-get update
    sudo apt-get install --yes docker docker-compose
    sudo adduser ubuntu docker
    cd /vagrant && git submodule update --init --recursive
  SHELL
end
