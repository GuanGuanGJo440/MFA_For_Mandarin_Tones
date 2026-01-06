############################################
# Chao Tone Relabeling Script (Mandarin)
############################################

toneTier = 1
pitchFloor = 75
pitchCeiling = 600
edgeOffset = 0.02

# --- Get selected objects ---
soundID = selected("Sound")
tgID    = selected("TextGrid")

if soundID = 0 or tgID = 0
    exitScript: "Please select one Sound and one TextGrid."
endif

# --- Create Pitch object ---
selectObject: soundID
To Pitch... 0.0 pitchFloor pitchCeiling
pitchID = selected("Pitch")

# --- Get speaker F0 range ---
selectObject: pitchID
f0min = Get minimum... 0 0 "Hertz"
f0max = Get maximum... 0 0 "Hertz"

step = (f0max - f0min) / 5

# --- Loop through intervals ---
selectObject: tgID
nIntervals = Get number of intervals... toneTier

for i from 1 to nIntervals
    startTime = Get start time of interval... toneTier i
    endTime   = Get end time of interval... toneTier i
    label$    = Get label of interval... toneTier i

    if label$ = "" then continue endif

    dur = endTime - startTime
    if dur < 0.05 then continue endif

    tStart = startTime + edgeOffset
    tMid   = startTime + dur / 2
    tEnd   = endTime - edgeOffset

    selectObject: pitchID
    f0s = Get value at time... tStart "Hertz" "Nearest"
    f0m = Get value at time... tMid   "Hertz" "Nearest"
    f0e = Get value at time... tEnd   "Hertz" "Nearest"

    levelS = floor ((f0s - f0min) / step) + 1
    levelM = floor ((f0m - f0min) / step) + 1
    levelE = floor ((f0e - f0min) / step) + 1

    if levelS < 1 then levelS = 1 endif
    if levelS > 5 then levelS = 5 endif
    if levelM < 1 then levelM = 1 endif
    if levelM > 5 then levelM = 5 endif
    if levelE < 1 then levelE = 1 endif
    if levelE > 5 then levelE = 5 endif

    if label$ = "3"
        newLabel$ = string$(levelS) + string$(levelM) + string$(levelE)
    else
        newLabel$ = string$(levelS) + string$(levelE)
    endif

    selectObject: tgID
    Set interval text... toneTier i newLabel$
endfor

selectObject: pitchID
Remove

printline "Chao tone relabeling completed."
