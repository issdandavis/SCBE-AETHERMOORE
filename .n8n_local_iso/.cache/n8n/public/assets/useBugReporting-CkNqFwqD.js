(function(){try{var e=typeof window<`u`?window:typeof global<`u`?global:typeof globalThis<`u`?globalThis:typeof self<`u`?self:{};e.SENTRY_RELEASE={id:`n8n@2.10.2`}}catch{}})();try{(function(){var e=typeof window<`u`?window:typeof global<`u`?global:typeof globalThis<`u`?globalThis:typeof self<`u`?self:{},t=new e.Error().stack;t&&(e._sentryDebugIds=e._sentryDebugIds||{},e._sentryDebugIds[t]=`1810c9e2-cff9-4aab-956d-a7f3aa7bbbf1`,e._sentryDebugIdIdentifier=`sentry-dbid-1810c9e2-cff9-4aab-956d-a7f3aa7bbbf1`)})()}catch{}import{Ot as e}from"./src-DayPUEod.js";import{js as t}from"./users.store-D10-L2pb.js";import{r as n}from"./_baseOrderBy-CZSwZsQe.js";function r(){let r=t(),i=n(),{isTouchDevice:a,userAgent:o}=e(),s=e=>{let t={n8nVersion:i.versionCli,platform:r.isDocker&&r.deploymentType===`cloud`?`docker (cloud)`:r.isDocker?`docker (self-hosted)`:`npm`,nodeJsVersion:r.nodeJsVersion,nodeEnv:r.nodeEnv,database:r.databaseType===`postgresdb`?`postgres`:r.databaseType,executionMode:r.isQueueModeEnabled?r.isMultiMain?`scaling (multi-main)`:`scaling (single-main)`:`regular`,concurrency:r.settings.concurrency,license:r.isCommunityPlan||!r.settings.license?`community`:r.settings.license.environment===`production`?`enterprise (production)`:`enterprise (sandbox)`};return e?t:{...t,consumerId:e?void 0:r.consumerId}},c=()=>({success:r.saveDataSuccessExecution,error:r.saveDataErrorExecution,progress:r.saveDataProgressExecution,manual:r.saveManualExecutions,binaryMode:r.binaryDataMode===`default`?`memory`:r.binaryDataMode}),l=()=>r.pruning?.isEnabled?{enabled:!0,maxAge:`${r.pruning?.maxAge} hours`,maxCount:`${r.pruning?.maxCount} executions`}:{enabled:!1},u=()=>{let e={};if(r.security.blockFileAccessToN8nFiles||(e.blockFileAccessToN8nFiles=!1),r.security.secureCookie||(e.secureCookie=!1),Object.keys(e).length!==0)return e},d=()=>({userAgent:o,isTouchDevice:a}),f=e=>{let t={core:s(e),storage:c(),pruning:l(),client:d()},n=u();return n&&(t.security=n),t},p=(e,{secondaryHeader:t})=>{let n=t?`#`:``,r=`${n}# Debug info\n\n`;for(let t in e){r+=`${n}## ${t}\n\n`;let i=e[t];if(i){for(let e in i){let t=i[e];r+=`- ${e}: ${t}\n`}r+=`
`}}return r},m=e=>`${e}Generated at: ${new Date().toISOString()}`;return{generateDebugInfo:({skipSensitive:e,secondaryHeader:t}={})=>m(p(f(e),{secondaryHeader:t}))}}const i={QUICKSTART_VIDEO:`https://www.youtube.com/watch?v=4cQWJViybAQ`,DOCUMENTATION:`https://docs.n8n.io?utm_source=n8n_app&utm_medium=app_sidebar`,FORUM:`https://community.n8n.io?utm_source=n8n_app&utm_medium=app_sidebar`,COURSES:`https://docs.n8n.io/courses/`};var a=`https://github.com/n8n-io/n8n/issues/new?labels=bug-report`,o=`
<!-- Please follow the template below. Skip the questions that are not relevant to you. -->

## Describe the problem/error/question


## What is the error message (if any)?


## Please share your workflow/screenshots/recording

\`\`\`
(Select the nodes on your canvas and use the keyboard shortcuts CMD+C/CTRL+C and CMD+V/CTRL+V to copy and paste the workflow.)
⚠️ WARNING ⚠️ If you have sensitive data in your workflow (like API keys), please remove it before sharing.
\`\`\`


## Share the output returned by the last node
<!-- If you need help with data transformations, please also share your expected output. -->

`;function s(){let e=r();return{getReportingURL:()=>{let t=new URL(a),n=`${o}\n${e.generateDebugInfo({skipSensitive:!0,secondaryHeader:!0})}}`;return t.searchParams.append(`body`,n),t.toString()}}}export{i as n,r,s as t};
//# sourceMappingURL=useBugReporting-CkNqFwqD.js.map