<template>
  <layout-text v-if="doc.id">
    <template v-slot:header>
      <toolbar-laptop
        :doc-id="doc.id"
        :enable-auto-labeling.sync="enableAutoLabeling"
        :guideline-text="project.guideline"
        :is-reviewd="doc.isConfirmed"
        :show-approve-button="project.permitApprove"
        :total="docs.count"
        class="d-none d-sm-block"
        @click:clear-label="clear"
        @click:review="confirm"
      />
      <toolbar-mobile
        :total="docs.count"
        class="d-flex d-sm-none"
      />
    </template>
    <template v-slot:content>
      <v-card class="mb-5">
        <v-card-text v-if="doc.text.startsWith('study-id-')" class="title">
          <div  style="height: 70vh; overflow: hidden">
            <iframe ref="iframe" class="ohif-frame" frameBorder="0" width="100%" height="100%" :src="study_url"></iframe>
          </div>
        </v-card-text>
        <v-card-text v-else class="title text-pre-wrap" v-text="doc.text" />
      </v-card>
      <seq2seq-box
        :text="doc.text"
        :annotations="annotations"
        @delete:annotation="remove"
        @update:annotation="update"
        @create:annotation="add"
      />
    </template>
    <template v-slot:sidebar>
      <list-metadata :metadata="doc.meta" />
    </template>
  </layout-text>
</template>

<script>
import _ from 'lodash'
import LayoutText from '@/components/tasks/layout/LayoutText'
import ListMetadata from '@/components/tasks/metadata/ListMetadata'
import ToolbarLaptop from '@/components/tasks/toolbar/ToolbarLaptop'
import ToolbarMobile from '@/components/tasks/toolbar/ToolbarMobile'
import Seq2seqBox from '~/components/tasks/seq2seq/Seq2seqBox'

export default {
  layout: 'workspace',

  components: {
    LayoutText,
    ListMetadata,
    Seq2seqBox,
    ToolbarLaptop,
    ToolbarMobile
  },

  async fetch() {
    this.docs = await this.$services.example.fetchOne(
      this.projectId,
      this.$route.query.page,
      this.$route.query.q,
      this.$route.query.isChecked
    )
    const doc = this.docs.items[0]
    if (this.enableAutoLabeling) {
      await this.autoLabel(doc.id)
    }
    await this.list(doc.id)
  },

  data() {
    return {
      annotations: [],
      docs: [],
      project: {},
      enableAutoLabeling: false
    }
  },

  computed: {
    projectId() {
      return this.$route.params.id
    },
    doc() {
      if (_.isEmpty(this.docs) || this.docs.items.length === 0) {
        return {}
      } else {
        return this.docs.items[0]
      }
    },
    study_url() {
      return "/ohif/viewer/"+ this.doc.text.substr(9);
    }
  },

  watch: {
    '$route.query': '$fetch',
    enableAutoLabeling(val) {
      if (val) {
        this.list(this.doc.id)
      }
    }
  },

  async created() {
    this.project = await this.$services.project.findById(this.projectId)
  },

  methods: {
    async list(docId) {
      this.annotations = await this.$services.seq2seq.list(this.projectId, docId)
    },

    async remove(id) {
      await this.$services.seq2seq.delete(this.projectId, this.doc.id, id)
      await this.list(this.doc.id)
    },

    async add(text) {
      await this.$services.seq2seq.create(this.projectId, this.doc.id, text)
      await this.list(this.doc.id)
    },

    async update(annotationId, text) {
      await this.$services.seq2seq.changeText(this.projectId, this.doc.id, annotationId, text)
      await this.list(this.doc.id)
    },

    async clear() {
      await this.$services.seq2seq.clear(this.projectId, this.doc.id)
      await this.list(this.doc.id)
    },

    async autoLabel(docId) {
      try {
        await this.$services.seq2seq.autoLabel(this.projectId, docId)
      } catch (e) {
        console.log(e.response.data.detail)
      }
    },

    async confirm() {
      await this.$services.example.confirm(this.projectId, this.doc.id)
      await this.$fetch()
    }
  },

  validate({ params, query }) {
    return /^\d+$/.test(params.id) && /^\d+$/.test(query.page)
  }
}
</script>

<style scoped>
.text-pre-wrap {
  white-space: pre-wrap !important;
}
.ohif-frame{
  position: relative;
  top: -40px;
}
</style>
