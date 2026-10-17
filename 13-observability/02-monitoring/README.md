helm upgrade -i prometheus prometheus-community/prometheus --namespace monitoring --set alertmanager.persistence.storageClass="gp2" --set server.persistentVolume.storageClass="gp2"
