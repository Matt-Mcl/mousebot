map = '<C><P /><Z><S><S L="271" H="40" X="400" Y="399" T="0" P="0,0,0.3,0.2,0,0,0,0" /></S><D><DS Y="360" X="402" /></D><O /></Z></C>'

tfm.exec.disableAutoShaman(true)
tfm.exec.disableAutoNewGame(true)
tfm.exec.disableAutoTimeLeft(true)

tfm.exec.newGame(map)

i = 0

function eventLoop(time, remaining)
    i = i + 1

    if i < 10 then
        return
    end

    if i % 4 == 0 then
        lcannon = tfm.exec.addShamanObject(17, -100, math.random(400), 90, -100, 0, false)
        rcannon = tfm.exec.addShamanObject(17, 900, math.random(400), -90, -100, 0, false)

    end

end
