<%!
    import medusa as app
    from medusa.common import Quality, qualityPresets, qualityPresetStrings
%>
<%
if not show is UNDEFINED:
    __quality = int(show.quality)
else:
    __quality = int(app.QUALITY_DEFAULT)
anyQualities, bestQualities = Quality.splitQuality(__quality)
overall_quality = Quality.combineQualities(anyQualities, bestQualities)
selected = None
%>
<select id="qualityPreset" name="quality_preset" class="form-control form-control-inline input-sm">
    <option value="0">Custom</option>
    % for curPreset in qualityPresets:
        <option value="${curPreset}" ${'selected="selected"' if curPreset == overall_quality else ''} ${('', 'style="padding-left: 15px;"')[qualityPresetStrings[curPreset].endswith("0p")]}>${qualityPresetStrings[curPreset]}</option>
    % endfor
</select>
<div id="customQualityWrapper">
    <div id="customQuality" style="padding-left: 0;">
        <p><b><strong>Preferred</strong></b> qualities will replace those in <b><strong>allowed</strong></b>, even if they are lower.</p>
        <div style="padding-right: 40px; text-align: left; float: left;">
            <h5>Allowed</h5>
            <% anyQualityList = filter(lambda x: x > Quality.NONE, Quality.qualityStrings) %>
            <select id="anyQualities" name="anyQualities" multiple="multiple" size="${len(anyQualityList)}" class="form-control form-control-inline input-sm">
            % for curQuality in sorted(anyQualityList):
                <option value="${curQuality}" ${'selected="selected"' if curQuality in anyQualities else ''}>${Quality.qualityStrings[curQuality]}</option>
            % endfor
            </select>
        </div>
        <div style="text-align: left; float: left;">
            <h5>Preferred</h5>
            <% bestQualityList = filter(lambda x: x >= Quality.SDTV and x < Quality.UNKNOWN, Quality.qualityStrings) %>
            <select id="bestQualities" name="bestQualities" multiple="multiple" size="${len(bestQualityList)}" class="form-control form-control-inline input-sm">
            % for curQuality in sorted(bestQualityList):
                <option value="${curQuality}" ${'selected="selected"' if curQuality in bestQualities else ''}>${Quality.qualityStrings[curQuality]}</option>
            % endfor
            </select>
        </div>
    </div>
</div>
