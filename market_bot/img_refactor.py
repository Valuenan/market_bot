import os

"""Входящийе файлы (photo_1@25-07-2022_13-25-11) и (photo_1@25-07-2022_13-25-11_thumb)"""

dir_name = 'products'
for root, dirs, files in os.walk(dir_name):
    for file in files:
        if file == 'no-image.jpg':
            continue

        if '@' in file and 'rev' not in file:
            file_oldname = os.path.join(root, file)

            if '_thumb' in file:
                """Тыльные строны"""
                file_split = file.split('@')
                file_newname_newfile = os.path.join(root, f'{file_split[0]}@rev.jpg')
                os.rename(file_oldname, file_newname_newfile)
            else:
                """Лицевые стороны"""
                file_split = file.split('@')
                file_newname_newfile = os.path.join(root, f'{file_split[0]}.jpg')
                os.rename(file_oldname, file_newname_newfile)
        else:
            continue
