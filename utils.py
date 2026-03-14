from .import local_dict


# cleanString: Sanitizes a string to be a valid GDL identifier.
# GDL identifiers must: contain no special characters, use underscores for spaces,
# be 28 chars or less (to leave room for prefixes like "ovr_sf_" up to AC's 36-char limit),
# and not clash with any GDL reserved keyword.
def cleanString(incomingString):
    newstring = incomingString
    newstring = newstring.replace("!","")
    newstring = newstring.replace("@","")
    newstring = newstring.replace("#","")
    newstring = newstring.replace("$","")
    newstring = newstring.replace("%","")
    newstring = newstring.replace("^","")
    newstring = newstring.replace("&","and")
    newstring = newstring.replace("*","")
    newstring = newstring.replace("(","")
    newstring = newstring.replace(")","")
    newstring = newstring.replace("+","")
    newstring = newstring.replace("=","")
    newstring = newstring.replace("?","")
    newstring = newstring.replace("\'","")
    newstring = newstring.replace("\"","")
    newstring = newstring.replace("{","")
    newstring = newstring.replace("}","")
    newstring = newstring.replace("[","")
    newstring = newstring.replace("]","")
    newstring = newstring.replace("<","")
    newstring = newstring.replace(">","")
    newstring = newstring.replace("~","")
    newstring = newstring.replace("`","")
    newstring = newstring.replace(":","")
    newstring = newstring.replace(";","")
    newstring = newstring.replace("|","")
    newstring = newstring.replace("\\","")
    newstring = newstring.replace("/","")        
    newstring = newstring.replace(".","")        
    newstring = newstring.replace(" ","_")        
    # Only French accent characters are handled. Other Unicode/accented characters
    # (German umlauts, Scandinavian chars, etc.) are not stripped and may cause issues.
    newstring = newstring.replace("é","e")
    newstring = newstring.replace("è","e")
    newstring = newstring.replace("à","a")
    if len(newstring) > 28:
        # Max Archicad identifier length is 36 chars.
        # We truncate at 28 to leave 8 chars of headroom for prefixes like "ovr_sf_" (7 chars).
        return newstring[0:28]
    else:
        # Prefix with "bl_" if the cleaned name is a reserved GDL keyword (e.g. "BASE", "BODY").
        # local_dict.gdl_keywords contains all reserved words in uppercase for case-insensitive comparison.
        if newstring.upper() in local_dict.gdl_keywords:
            return "bl_" + newstring
        return newstring