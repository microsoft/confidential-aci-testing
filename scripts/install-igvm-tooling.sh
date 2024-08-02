git clone https://github.com/microsoft/igvm-tooling.git /tmp/igvm_tooling
(
    cd /tmp/igvm_tooling/src
    sudo apt-get update && sudo apt-get install acpica-tools
    pip3 install ./
)

sudo apt-get update && sudo apt-get install acpica-tools bc