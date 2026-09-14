FROM eclipse-temurin:21-jre@sha256:a80c51f2d09a3e7e00d521f1c817bbceb6b3be94109b4a784d46078099882dda
WORKDIR /opt/synthea
# Official v4.0.0 release; checksum published by GitHub's release API.
ADD --checksum=sha256:ed43c20ad40ba5c3bc724503a5af032715fe3c491620b766148e7c2361e6ecc1 https://github.com/synthetichealth/synthea/releases/download/v4.0.0/synthea-with-dependencies.jar /opt/synthea/synthea.jar
ENV TZ=UTC
ENTRYPOINT ["java", "-Xmx2g", "-Duser.timezone=UTC", "-jar", "/opt/synthea/synthea.jar"]
