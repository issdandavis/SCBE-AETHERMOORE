-- bookforge: convert markdown horizontal rules into a typeset scene break.

function HorizontalRule(_)
  local raw = "\\par\\vspace{0.6em}\\noindent\\hfill" ..
              "\\textasteriskcentered\\quad\\textasteriskcentered\\quad\\textasteriskcentered" ..
              "\\hfill\\null\\par\\vspace{0.6em}"
  return pandoc.RawBlock("latex", raw)
end
