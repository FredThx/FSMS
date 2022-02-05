sudo systemctl stop sms_server.service
rsync -av --exclude-from=ExclusionRSync /home/pi/Devlopp/FSMS/ /opt/sms
sudo systemctl start sms_server.service
