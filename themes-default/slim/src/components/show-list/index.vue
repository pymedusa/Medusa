<template>
    <div>
        <!-- <h1 v-if="header" class="header">{{ listTitle }}</h1> -->
        <div class="showListTitle listTitle">
            <button type="button" class="nav-show-list move-show-list">
                <span class="icon-bar"></span>
                <span class="icon-bar"></span>
                <span class="icon-bar"></span>
            </button>
            <h2 class="header">{{listTitle}}</h2>
        </div>
        <div v-if="shows.length >= 1" :class="[['simple', 'small', 'banner'].includes(layout) ? 'table-layout' : '']">
            <component :is="mappedLayout" v-bind="$props" />
        </div>

        <span v-else>Please add a show <a href="/addShows">here</a> to get started</span>
    </div>
</template>
<script>

import Banner from './banner.vue';
import Simple from './simple.vue';
import Poster from './poster.vue';
import Smallposter from './smallposter.vue';

export default {
    name: 'show-list',
    components: {
        Banner,
        Simple,
        Poster,
        Smallposter
    },
    props: {
        layout: {
            validator: layout => [
                null,
                '',
                'poster',
                'banner',
                'simple',
                'small'
            ].includes(layout),
            required: true
        },
        shows: {
            type: Array,
            required: true
        },
        listTitle: {
            type: String
        },
        header: {
            type: Boolean
        }
    },
    computed: {
        mappedLayout() {
            const { layout } = this;
            if (layout === 'small') {
                return 'smallposter';
            }
            return layout;
        }
    }
};
</script>
<style scoped>

/** Use this as table styling for all table layouts */
.table-layout >>> .vgt-table {
    width: 100%;
    margin-right: auto;
    margin-left: auto;
    color: rgb(0, 0, 0);
    text-align: left;
    background-color: rgb(221, 221, 221);
    border-spacing: 0;
}

.table-layout >>> .vgt-table th,
.table-layout >>> .vgt-table td {
    padding: 4px;
    border-top: rgb(255, 255, 255) 1px solid;
    border-left: rgb(255, 255, 255) 1px solid;
    vertical-align: middle;
}

/* remove extra border from left edge */
.table-layout >>> .vgt-table th:first-child,
.table-layout >>> .vgt-table td:first-child {
    border-left: none;
}

.table-layout >>> .vgt-table th {
    color: rgb(255, 255, 255);
    text-align: center;
    text-shadow: -1px -1px 0 rgba(0, 0, 0, 0.3);
    background-color: rgb(51, 51, 51);
    border-collapse: collapse;
    font-weight: normal;
}

.table-layout >>> .vgt-table span.break-word {
    word-wrap: break-word;
}

.table-layout >>> .vgt-table thead th.sorting.sorting-desc {
    background-color: rgb(85, 85, 85);
    background-image: url(data:image/gif;base64,R0lGODlhFQAEAIAAAP///////yH5BAEAAAEALAAAAAAVAAQAAAINjB+gC+jP2ptn0WskLQA7);
}

.table-layout >>> .vgt-table thead th.sorting.sorting-asc {
    background-color: rgb(85, 85, 85);
    background-image: url(data:image/gif;base64,R0lGODlhFQAEAIAAAP///////yH5BAEAAAEALAAAAAAVAAQAAAINjI8Bya2wnINUMopZAQA7);
    background-position-x: right;
    background-position-y: bottom;
}

.table-layout >>> .vgt-table thead th.sorting {
    background-repeat: no-repeat;
}

.table-layout >>> .vgt-table thead th {
    background-image: none;
    padding: 4px;
    cursor: default;
}

.table-layout >>> .vgt-table input.tablesorter-filter {
    width: 98%;
    height: auto;
    -webkit-box-sizing: border-box;
    -moz-box-sizing: border-box;
    box-sizing: border-box;
}

.table-layout >>> .vgt-table tr.tablesorter-filter-row,
.table-layout >>> .vgt-table tr.tablesorter-filter-row td {
    text-align: center;
}

/* optional disabled input styling */
.table-layout >>> .vgt-table input.tablesorter-filter-row .disabled {
    display: none;
}

.tablesorter-header-inner {
    padding: 0 2px;
    text-align: center;
}

.table-layout >>> .vgt-table tfoot tr {
    color: rgb(255, 255, 255);
    text-align: center;
    text-shadow: -1px -1px 0 rgba(0, 0, 0, 0.3);
    background-color: rgb(51, 51, 51);
    border-collapse: collapse;
}

.table-layout >>> .vgt-table tfoot a {
    color: rgb(255, 255, 255);
    text-decoration: none;
}

.table-layout >>> .vgt-table th.vgt-row-header {
    text-align: left;
}

.table-layout >>> .vgt-table .season-header {
    display: inline;
    margin-left: 5px;
}

.table-layout >>> .vgt-table tr.spacer {
    height: 25px;
}

/* .unaired {
    background-color: rgb(245, 241, 228);
}

.skipped {
    background-color: rgb(190, 222, 237);
}

.preferred {
    background-color: rgb(195, 227, 200);
}

.archived {
    background-color: rgb(195, 227, 200);
}

.allowed {
    background-color: rgb(255, 218, 138);
}

.wanted {
    background-color: rgb(255, 176, 176);
}

.snatched {
    background-color: rgb(235, 193, 234);
}

.downloaded {
    background-color: rgb(195, 227, 200);
}

.failed {
    background-color: rgb(255, 153, 153);
}

span.unaired {
    color: rgb(88, 75, 32);
}

span.skipped {
    color: rgb(29, 80, 104);
}

span.preffered {
    color: rgb(41, 87, 48);
}

span.allowed {
    color: rgb(118, 81, 0);
}

span.wanted {
    color: rgb(137, 0, 0);
}

span.snatched {
    color: rgb(101, 33, 100);
}

span.unaired b,
span.skipped b,
span.preferred b,
span.allowed b,
span.wanted b,
span.snatched b {
    color: rgb(0, 0, 0);
    font-weight: 800;
} */

/* td.col-footer {
    text-align: left !important;
}

.vgt-wrap__footer {
    color: rgb(255, 255, 255);
    padding: 1em;
    background-color: rgb(51, 51, 51);
    margin-bottom: 1em;
    display: flex;
    justify-content: space-between;
} */

/* .footer__row-count,
.footer__navigation__page-info {
    display: inline;
}

.footer__row-count__label {
    margin-right: 1em;
}

.vgt-wrap__footer .footer__navigation {
    font-size: 14px;
} */

/* .vgt-pull-right {
    float: right !important;
} */

.align-center {
    display: flex;
    justify-content: center;
}

</style>
