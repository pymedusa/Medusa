function metaToBool(pyVar){
    var meta = $("meta[data-var='" + pyVar + "']").data("content");
    if(typeof meta === "undefined"){
        console.log(pyVar + " is empty, did you forget to add this to main.mako?");
        return meta;
    } else {
        meta = (isNaN(meta) ? meta.toLowerCase() : meta.toString());
        return !(meta === "false" || meta === "none" || meta === "0");
    }
}

function getMeta(pyVar){
    return $("meta[data-var='" + pyVar + "']").data("content");
}

var srRoot = getMeta("srRoot");



$(document).ready(function(){
    if (metaToBool("FANART_BACKGROUND")) {
        $.backstretch(srRoot + "/showPoster/?show=" + $("#showID").attr("value") + "&which=fanart");
        $(".backstretch").css("opacity", getMeta("FANART_BACKGROUND_OPACITY")).fadeIn("500");
    }
    $(".seriesCheck").click(function(){
        var serCheck = this;

        $(".seasonCheck:visible").each(function(){
            this.checked = serCheck.checked;
        });

        $(".epCheck:visible").each(function(){
            this.checked = serCheck.checked;
        });
    });

    $(".seasonCheck").click(function(){
        var seasCheck = this;
        var seasNo = $(seasCheck).attr("id");

        $(".epCheck:visible").each(function(){
            var epParts = $(this).attr("id").split("x");

            if (epParts[0] === seasNo) {
                this.checked = seasCheck.checked;
            }
        });
    });

    $("input[type=submit]").click(function(){
        var epArr = [];

        $(".epCheck").each(function() {
            if (this.checked === true) {
                epArr.push($(this).attr("id"));
            }
        });

        if (epArr.length === 0) { return false; }

        window.location.href = srRoot+"/home/doRename?show="+$("#showID").attr("value")+"&eps="+epArr.join("|");
    });

});
