<div v-if="config.animeSplitHome && config.animeSplitHomeInTabs" v-for="(shows, listTitle) in showLists" :key="listTitle" :id="listTitle + 'TabContent'">
    <show-list v-bind="{ listTitle, layout, shows, header: true, sortArticle: config.sortArticle }"></show-list>
</div> <!-- #...TabContent -->
<show-list v-for="(shows, listTitle) in showLists" :key="listTitle" v-bind="{ listTitle, layout, shows, header: Object.keys(showLists).length > 1, sortArticle: config.sortArticle }"></show-list>
