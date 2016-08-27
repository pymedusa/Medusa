<%inherit file="/layouts/main.mako"/>
<%!
    import medusa as app
    from medusa.helpers import anon_url
%>
<%block name="content">
<div id="content960">
    <h1 class="header">${header}</h1>
    <div id="config">
        <div id="config-content">
            <form id="configForm" action="config/anime/saveAnime" method="post">
                <div id="config-components" class="ui-tabs">
                    <ul>
                        <li><a href="config/anime/#animedb-settings">AnimeDB Settings</a></li>
                        <li><a href="config/anime/#anime-look-feel">Look &amp; Feel</a></li>
                    </ul>
                    <div data-tab-id="animedb-settings" class="component-group">
                        <div class="component-group-desc">
                            <span class="icon-notifiers-anime" title="AniDB"></span>
                            <h3>
                                <a href="${anon_url('http://anidb.info')}" onclick="window.open(this.href, '_blank'); return false;">AniDB</a>
                            </h3>
                            <p>AniDB is non-profit database of anime information that is freely open to the public</p>
                        </div><!-- .component-group-desc //-->
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <input type="checkbox" class="enabler" name="use_anidb" id="use_anidb" ${'checked="checked"' if app.USE_ANIDB else ''} />
                                <label for="use_notifo">
                                    <span class="component-title">Enable</span>
                                    <span class="component-desc">Should Medusa use data from AniDB?</span>
                                </label>
                            </div><!-- .field-pair //-->
                            <div id="content_use_anidb">
                                <div class="field-pair">
                                    <label class="nocheck">
                                        <span class="component-title">AniDB Username</span>
                                        <input type="text" name="anidb_username" id="anidb_username" value="${app.ANIDB_USERNAME}" class="form-control input-sm input350"
                                               autocomplete="no" />
                                    </label>
                                    <label class="nocheck">
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">Username of your AniDB account</span>
                                    </label>
                                </div><!-- .field-pair //-->
                                <div class="field-pair">
                                    <label class="nocheck">
                                        <span class="component-title">AniDB Password</span>
                                        <input type="password" name="anidb_password" id="anidb_password" value="${app.ANIDB_PASSWORD}" class="form-control input-sm input350" autocomplete="no"/>
                                    </label>
                                    <label class="nocheck">
                                        <span class="component-title">&nbsp;</span>
                                        <span class="component-desc">Password of your AniDB account</span>
                                    </label>
                                </div><!-- .field-pair //-->
                                <div class="field-pair">
                                    <input type="checkbox" name="anidb_use_mylist" id="anidb_use_mylist" ${'checked="checked"' if app.ANIDB_USE_MYLIST else ''}/>
                                    <label>
                                        <span class="component-title">AniDB MyList</span>
                                        <span class="component-desc">Do you want to add the PostProcessed Episodes to the MyList ?</span>
                                    </label>
                                </div><!-- .field-pair //-->
                            </div><!-- #content_use_anidb //-->
                            <input type="submit" class="btn config_submitter" value="Save Changes" />
                        </fieldset><!-- .component-group-list //-->
                    </div><!-- #animedb-settings //-->
                    <div data-tab-id="anime-look-feel" class="component-group">
                        <div class="component-group-desc">
                            <span class="icon-notifiers-look" title="look"></span>
                            <h3>Look and Feel</h3>
                            <p>How should the anime functions show and behave.</p>
                       </div><!-- .component-group-desc //-->
                        <fieldset class="component-group-list">
                            <div class="field-pair">
                                <input type="checkbox" class="enabler" name="split_home" id="split_home" ${'checked="checked"' if app.ANIME_SPLIT_HOME else ''}/>
                                <label for="use_notifo">
                                    <span class="component-title">Split show lists</span>
                                    <span class="component-desc">Separate anime and normal shows in groups</span>
                                </label>
                            </div><!-- .field-pair //-->
                            <input type="submit" class="btn config_submitter" value="Save Changes" />
                       </fieldset><!-- .component-group-list //-->
                    </div><!-- #anime-look-feel //-->
                    <br>
                    <input type="submit" class="btn config_submitter" value="Save Changes" />
                    <br>
                </div><!-- #config-components //-->
            </form><!-- #configForm //-->
        </div><!-- #config-content //-->
    </div><!-- #config //-->
</div><!-- #content960 //-->
</%block>
