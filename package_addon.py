import os
import zipfile
import glob

def create_zip(zip_name, files_to_include, folder_mapping=None):
    if folder_mapping is None:
        folder_mapping = {}
        
    print(f"Creating {zip_name}...")
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in files_to_include:
            if os.path.exists(f):
                if os.path.isdir(f):
                    for root, dirs, files in os.walk(f):
                        # skip pycache
                        if '__pycache__' in root:
                            continue
                        for file in files:
                            if file.endswith('.pyc'):
                                continue
                            file_path = os.path.join(root, file)
                            arcname = file_path
                            zf.write(file_path, arcname)
                else:
                    arcname = folder_mapping.get(f, f)
                    zf.write(f, arcname)
            else:
                print(f"Warning: {f} not found!")
    print(f"Successfully created {zip_name}")

def main():
    # 1. ArcGIS Pro Add-on Zip
    arcgis_files = [
        'Install-AntigravityGIS.bat',
        'Install-AntigravityGIS.ps1',
        'Uninstall-AntigravityGIS.ps1',
        'installer_gui.py',
        'chat_gui.py',
        'chat_gui.pyw',
        'agent_core.py',
        'version.json',
        'arcgis' # Directory
    ]
    create_zip('releases/Install-AntigravityGIS-Setup.zip', arcgis_files)

    # 2. QGIS Add-on Zip
    qgis_files = [
        'Install-AntigravityGIS-QGIS.bat',
        'Install-AntigravityGIS-QGIS.ps1',
        'Uninstall-AntigravityGIS-QGIS.ps1',
        'agent_core.py',
        'version.json',
        'qgis'
    ]
    create_zip('releases/Install-AntigravityGIS-QGIS-Setup.zip', qgis_files)

if __name__ == '__main__':
    main()
