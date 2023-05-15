import PySimpleGUI as sg
import os.path
import sys
import timeclock
from datetime import datetime, timedelta


# First the window layout in 2 columns
sg.theme("DarkAmber")

timeclock = timeclock.TimeClock()
yl = timeclock.ls("year", datetime.now()) 

explorer_frame = [
    [
        sg.Text("Keywords"),
        sg.In(size=(25, 1), enable_events=True, key="-KEYWORDS-"),
    ],
    [
        sg.Listbox(
            values=yl, enable_events=True, size=(40, 20), key="-FILE LIST-"
        )
    ],
]

colsize = (11,1)
value_column = [
    [sg.Text("Duration:",size=colsize, key="-HELP-"),sg.Text(size=(40, 1), key="-TOUT-")],
    [sg.Text("Start:",size=colsize),sg.In(size=(40, 1),key="-START-", enable_events=True)],
    [sg.Text("End:",size=colsize),sg.In(size=(40, 1), key="-END-")],
    [sg.Text("Description:",size=colsize),sg.Multiline(key="-DESCRIPTION-", size=(40,10), no_scrollbar=True, autoscroll=False)],
    [sg.Button("Save", key='-SAVE-')]
]


# For now will only show the name of the file that was chosen


# ----- Full layout -----
layout = [
    [
        sg.Column(explorer_frame),
        sg.VSeperator(),
        sg.Column(value_column)
    ]
]


window = sg.Window("TimeClock", layout, finalize=True)
window["-FILE LIST-"].bind('<Double-Button-1>' , "+-double click-")
window['-START-'].bind("<Button-1>", "+-click-")


window["-HELP-"].update("")
window["-START-"].hide_row()
window["-END-"].hide_row()
window["-DESCRIPTION-"].hide_row()
window["-SAVE-"].hide_row()


context = None

oldStart = ""

# Run the Event Loop
while True:

    event, values = window.read()
    if event == "Exit" or event == sg.WIN_CLOSED:
        break

    print(event)

    if event == "-SAVE-":
        pass

    # Folder name was filled in, make a list of files in the folder
    if event == "-FOLDER-":
        folder = values["-FOLDER-"]
        try:
            # Get list of files in folder
            file_list = timeclock.ls()
        except:
            file_list = []

        fnames = [
            f
            for f in file_list
            if os.path.isfile(os.path.join(folder, f))
            and f.lower().endswith((".png", ".gif"))
        ]
        window["-FILE LIST-"].update(fnames)


    elif event == '-FILE LIST-':


        # try:
            # Set defaults
            window["-HELP-"].update("Duration:")
            window["-START-"].hide_row()
            window["-END-"].hide_row()
            window["-DESCRIPTION-"].hide_row()
            window["-SAVE-"].hide_row()


            dateStr = values["-FILE LIST-"][0]
            if dateStr == "..":
                window["-HELP-"].update("Action:")
                window["-TOUT-"].update("Navigate up")
                continue
            date, mode = timeclock.parseDate(dateStr)

            start = date
            end = date

            if date and mode == "slot":
                slot = timeclock.getSlot(dateStr)
                duration = timeclock.datetimeFromString(slot['end']) - timeclock.datetimeFromString(slot['start'])
                description = ""
                if 'description' in slot:
                    description = slot['description']
                window["-TOUT-"].update(timeclock.formatDuration(duration))
                window["-START-"].update(slot['start'])
                window["-END-"].update(slot['end'])
                window["-DESCRIPTION-"].update(description)


                window["-START-"].unhide_row()
                window["-END-"].unhide_row()
                window["-DESCRIPTION-"].unhide_row()
                window["-SAVE-"].unhide_row()
                continue
            if date and mode == "day":
                end = date + timedelta(days=1)
            if date and mode == "week":
                start, end = timeclock.getWeek(date)
            if date and mode == "month":
                start, end = timeclock.getMonth(date)
            if date and mode == "year":
                end = date + timedelta(days=356)

            duration = timeclock.summary(start, end)
            window["-TOUT-"].update(timeclock.formatDuration(duration))


        # except Exception as e:
        #     print(e)
        #     exc_type, exc_obj, exc_tb = sys.exc_info()
        #     fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        #     print(exc_type, fname, exc_tb.tb_lineno)


    elif event == "-FILE LIST-+-double click-":  # A file was chosen from the listbox
        try:
            dateStr = values["-FILE LIST-"][0]
            if dateStr == "..":
                dateStr = ' '.join(context.split(" ")[1:])

            date, mode = timeclock.parseDate(dateStr)

            if mode == "slot":
                continue

            new = [".."]
            context = dateStr
                
            details = ""
            res = timeclock.ls(mode, date)
            if mode == None:
                window["-FILE LIST-"].update(res)
                window["-TOUT-"].update(details)
                continue

            if mode == "day":
                for e in res:
                    print(e)
                    new.append(e['start'])
                window["-FILE LIST-"].update(new)
            else:
                for e in res:
                    new.append(e)
                window["-FILE LIST-"].update(new)

            window["-TOUT-"].update(details)

        except Exception as e:
            print(e)
    elif event == "-SAVE-":
        if oldStart == "":
            oldStart = values['-START-']
            print("Start didnt change")
        date = timeclock.datetimeFromString(oldStart)
        start = timeclock.datetimeFromString(values["-START-"])
        end = timeclock.datetimeFromString(values["-END-"])
        description = values["-DESCRIPTION-"]

        timeclock.updateSlot(date, start, end, description)
        oldStart = ""

    elif event == "-START-+-click-":
        oldStart = values["-START-"]



window.close()

