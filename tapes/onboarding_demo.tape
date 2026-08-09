Output docs/assets/recordings/onboarding_demo.gif

# Import shared appearance configuration
Source tapes/_common.tape

# Setup temporary environment
Type "netflix-narc"
Enter
Sleep 1.5s

# Navigate through onboarding wizard
Type "10"
Sleep 500ms
Enter
Sleep 1s

# Toggle weight slider
Down 2
Right 3
Sleep 1s

# Finish setup
Enter
Sleep 2s
