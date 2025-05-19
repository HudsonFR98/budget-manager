# -*- mode: ruby -*-

Vagrant.configure("2") do |config|
  config.vm.provider :virtualbox do |vb|
    vb.customize ["modifyvm", :id, "--usb", "off"]
    vb.customize ["modifyvm", :id, "--memory", "1048"]
  end

  config.vm.define :fair3r_custom_overlay do |conf|
    conf.vm.box = "debian/stretch64"
    conf.vm.network "private_network", ip: "33.33.33.60"
    conf.vm.synced_folder "e:\\ics_src", "/ics_src", :create => true
  end
end
