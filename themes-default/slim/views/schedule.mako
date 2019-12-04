<%inherit file="/layouts/main.mako"/>
<%!
    from random import choice

    from medusa import app
%>
<%block name="scripts">
<script type="text/javascript" src="js/ajax-episode-search.js?${sbPID}"></script>

<script type="text/x-template" id="schedule-template">
<div>
    <% random_series = choice(results) if results else '' %>
    <backstretch slug="${choice(results)['series_slug'] if results else ''}"></backstretch>
    
    <div class="row">
        <div class="col-md-12">
            <h1 class="header">{{header}}</h1>
        </div>
    </div>
    
    <div class="row">
        <div class="col-md-12">
            <div class="key pull-left">
                <template v-if="scheduleLayout !== 'calendar'">
                    <b>Key:</b>
                    <span class="listing-key listing-overdue">Missed</span>
                    <span class="listing-key listing-current">Today</span>
                    <span class="listing-key listing-default">Soon</span>
                    <span class="listing-key listing-toofar">Later</span>
                </template>
                <app-link class="btn-medusa btn-inline forceBacklog" href="webcal://${sbHost}:${sbHttpPort}/calendar">
                <i class="icon-calendar icon-white"></i>Subscribe</app-link>
            </div>
    
            <div class="pull-right">
                <div class="show-option">
                    <span>View Paused:
                        <select name="viewpaused" class="form-control form-control-inline input-sm" onchange="location = this.options[this.selectedIndex].value;">
                            <option value="schedule/toggleScheduleDisplayPaused" ${'selected="selected"' if not bool(app.COMING_EPS_DISPLAY_PAUSED) else ''}>Hidden</option>
                            <option value="schedule/toggleScheduleDisplayPaused" ${'selected="selected"' if app.COMING_EPS_DISPLAY_PAUSED else ''}>Shown</option>
                        </select>
                    </span>
                </div>
                <div class="show-option">
                    <span>Layout:
                        <select v-model="scheduleLayout" name="layout" class="form-control form-control-inline input-sm show-layout">
                            <option :value="option.value" v-for="option in layoutOptions" :key="option.value">{{ option.text }}</option>
                        </select>
                    </span>
                </div>
                <div v-if="scheduleLayout === 'list'" class="show-option">
                    <button id="popover" type="button" class="btn-medusa btn-inline">Select Columns <b class="caret"></b></button>
                </div>
                <!-- Calendar sorting is always by date -->
                <div v-else-if="scheduleLayout !== 'calendar'" class="show-option">
                    <span>Sort By:
                        <select name="sort" class="form-control form-control-inline input-sm" onchange="location = 'schedule/setScheduleSort/?sort=' + this.options[this.selectedIndex].value;">
                            <option value="date" ${'selected="selected"' if app.COMING_EPS_SORT == 'date' else ''}>Date</option>
                            <option value="network" ${'selected="selected"' if app.COMING_EPS_SORT == 'network' else ''}>Network</option>
                            <option value="show" ${'selected="selected"' if app.COMING_EPS_SORT == 'show' else ''}>Show</option>
                        </select>
                    </span>
                </div>
            </div>
        </div>
    </div>
    
    <div class="horizontal-scroll">
        <%include file="/partials/schedule/${layout}.mako"/>
    </div> <!-- end horizontal scroll -->
    <div class="clearfix"></div>    
</div>
</script>
<script>
    window.app = new Vue({
        el: '#vue-wrap',
        store,
        router,
        data() {
            return {
                // This loads schedule.vue
                pageComponent: 'schedule'
            }
        }
    });
</script>
</%block>