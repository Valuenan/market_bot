import os

"""Входящийе файлы (photo_1@25-07-2022_13-25-11) и (photo_1@25-07-2022_13-25-11_thumb)
    Файлы с _thumb для телеграмм, без для 1с"""

""""Использовать код по очереди"""

root_dir = 'products'
c_dir = 'products/1c'
for root, dirs, files in os.walk(root_dir):
    for file in files:
        if file == 'no-image.jpg':
            continue
        file_oldname = os.path.join(root, file)
        if '_thumb' not in file:
            file_destination = f'{root}/1c/{file}'
            os.replace(f'{root}/{file}', file_destination)
            continue

        if '@' in file and 'rev' not in file:
            file_split = file.split('@')
            name, num = file_split[0].split('_')
            if int(num) % 2 == 0:
                """Тыльные строны"""
                file_newname_newfile = os.path.join(root, f'{name}{int(num) - 1}@rev.jpg')
                os.rename(file_oldname, file_newname_newfile)
            else:
                """Лицевые стороны"""

                file_newname_newfile = os.path.join(root, f'{name}{int(num)}.jpg')
                os.rename(file_oldname, file_newname_newfile)
        else:
            continue
#
# for root, dirs, files in os.walk(c_dir):
#     for file in files:
#         for file in files:
#             file_oldname = os.path.join(root, file)
#             if '@' in file and 'rev' not in file:
#                 file_split = file.split('@')
#                 name, num = file_split[0].split('_')
#                 if int(num) % 2 == 0:
#                     """Тыльные строны"""
#                     file_newname_newfile = os.path.join(root, f'{name}{int(num) - 1}@rev.jpg')
#                     os.rename(file_oldname, file_newname_newfile)
#                 else:
#                     """Лицевые стороны"""
#
#                     file_newname_newfile = os.path.join(root, f'{name}{int(num)}.jpg')
#                     os.rename(file_oldname, file_newname_newfile)
#             else:
#                 continue