var allExceptions = [];

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
        $.backstretch(srRoot + "/showPoster/?show=" + $("#show").attr("value") + "&which=fanart");
        $(".backstretch").css("opacity", getMeta("FANART_BACKGROUND_OPACITY")).fadeIn("500");
    }
});

$("#location").fileBrowser({ title: "Select Show Location" });

$("#submit").click(function() {
    var allExceptions = [];

    $("#exceptions_list option").each(function() {
        allExceptions.push( $(this).val() );
    });

    $("#exceptions_list").val(allExceptions);

    if(metaToBool("show.is_anime")) { generateBlackWhiteList(); }
});
$("#addSceneName").click(function() {
    var sceneEx = $("#SceneName").val();
    var option = $("<option>");
    allExceptions = [];

    $("#exceptions_list option").each(function() {
        allExceptions.push($(this).val());
    });

    $("#SceneName").val("");

    if ($.inArray(sceneEx, allExceptions) > -1 || (sceneEx === "")) { return; }

    $("#SceneException").show();

    option.prop("value", sceneEx);
    option.html(sceneEx);
    return option.appendTo("#exceptions_list");
});

$("#removeSceneName").click(function() {
    $("#exceptions_list option:selected").remove();

    $(this).toggleSceneException();
});

$.fn.toggleSceneException = function() {
    allExceptions = [];

    $("#exceptions_list option").each  ( function() {
        allExceptions.push( $(this).val() );
    });

    if (allExceptions === ""){
        $("#SceneException").hide();
    } else {
        $("#SceneException").show();
    }
};

$(this).toggleSceneException();
