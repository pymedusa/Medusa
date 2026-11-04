<template>
    <div class="footer__row-count vgt-pull-left">
        <label :for="id" class="footer__row-count__label">Rows per page:</label>
        <select :id="id" name="perPageSelect" class="footer__row-count__select"
                :value="value" @change="$emit('input', Number($event.target.value))">
            <option v-for="size in options" :key="size" :value="size">{{size}}</option>
            <option :value="-1">All</option>
        </select>
    </div>
</template>

<script>
export const formatPaginationInfo = (info, perPage) => {
    const { firstRecordOnPage, lastRecordOnPage, totalRecords } = info;
    const first = totalRecords === 0 ? 0 : (perPage === -1 ? 1 : firstRecordOnPage);
    const last = perPage === -1 ? totalRecords : lastRecordOnPage;
    return `${first} - ${last} of ${totalRecords}`;
};

export default {
    name: 'table-page-size',
    props: {
        id: { type: String, required: true },
        value: { type: Number, required: true },
        options: { type: Array, required: true }
    }
};
</script>
