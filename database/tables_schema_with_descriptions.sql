/*
  BlogDB 全量表结构与字段说明脚本（SQL Server）
  ===========================================
  生成日期：2026-04-15
  目标：
  1) 创建当前后端模型所需全部表；
  2) 创建关键索引、唯一约束、外键；
  3) 写入表/字段 MS_Description 注释（可重复执行）。
*/

USE BlogDB;
GO

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

/* ==================== 基础表 ==================== */
IF OBJECT_ID(N'dbo.users', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.users (
        id              INT            IDENTITY(1,1) NOT NULL PRIMARY KEY,
        username        NVARCHAR(64)   NOT NULL,
        hashed_password NVARCHAR(255)  NOT NULL,
        is_active       BIT            NOT NULL CONSTRAINT DF_users_is_active DEFAULT (1),
        created_at      DATETIME2(3)   NOT NULL
    );
END
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.users') AND name = N'UQ_users_username')
    CREATE UNIQUE INDEX UQ_users_username ON dbo.users(username);
GO

IF OBJECT_ID(N'dbo.categories', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.categories (
        id         INT            IDENTITY(1,1) NOT NULL PRIMARY KEY,
        name       NVARCHAR(128)  NOT NULL,
        slug       NVARCHAR(128)  NOT NULL,
        created_at DATETIME2(3)   NOT NULL,
        updated_at DATETIME2(3)   NOT NULL
    );
END
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.categories') AND name = N'UQ_categories_slug')
    CREATE UNIQUE INDEX UQ_categories_slug ON dbo.categories(slug);
GO

IF OBJECT_ID(N'dbo.tags', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.tags (
        id         INT           IDENTITY(1,1) NOT NULL PRIMARY KEY,
        name       NVARCHAR(64)  NOT NULL,
        slug       NVARCHAR(64)  NOT NULL,
        created_at DATETIME2(3)  NOT NULL
    );
END
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.tags') AND name = N'UQ_tags_slug')
    CREATE UNIQUE INDEX UQ_tags_slug ON dbo.tags(slug);
GO

/* ==================== 文章与评论 ==================== */
IF OBJECT_ID(N'dbo.posts', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.posts (
        id              INT            IDENTITY(1,1) NOT NULL PRIMARY KEY,
        title           NVARCHAR(255)  NOT NULL,
        slug            NVARCHAR(255)  NOT NULL,
        excerpt         NVARCHAR(500)  NULL,
        content         NVARCHAR(MAX)  NOT NULL,
        published       BIT            NOT NULL CONSTRAINT DF_posts_published DEFAULT (0),
        review_status   NVARCHAR(20)   NOT NULL CONSTRAINT DF_posts_review_status DEFAULT (N'draft'),
        cover_image_url NVARCHAR(512)  NULL,
        favorite_count  INT            NOT NULL CONSTRAINT DF_posts_favorite_count DEFAULT (0),
        like_count      INT            NOT NULL CONSTRAINT DF_posts_like_count DEFAULT (0),
        view_count      INT            NOT NULL CONSTRAINT DF_posts_view_count DEFAULT (0),
        share_count     INT            NOT NULL CONSTRAINT DF_posts_share_count DEFAULT (0),
        rank_level      INT            NOT NULL CONSTRAINT DF_posts_rank_level DEFAULT (1),
        weight          INT            NOT NULL CONSTRAINT DF_posts_weight DEFAULT (0),
        hot_score       INT            NOT NULL CONSTRAINT DF_posts_hot_score DEFAULT (0),
        is_featured     BIT            NOT NULL CONSTRAINT DF_posts_is_featured DEFAULT (0),
        is_pinned       BIT            NOT NULL CONSTRAINT DF_posts_is_pinned DEFAULT (0),
        published_at    DATETIME2(3)   NULL,
        offline_at      DATETIME2(3)   NULL,
        content_type    NVARCHAR(20)   NULL,
        source_url      NVARCHAR(512)  NULL,
        created_at      DATETIME2(3)   NOT NULL,
        updated_at      DATETIME2(3)   NOT NULL,
        author_id       INT            NULL,
        category_id     INT            NULL
    );
END
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.posts') AND name = N'UQ_posts_slug')
    CREATE UNIQUE INDEX UQ_posts_slug ON dbo.posts(slug);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.posts') AND name = N'IX_posts_author_id')
    CREATE INDEX IX_posts_author_id ON dbo.posts(author_id);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.posts') AND name = N'IX_posts_category_id')
    CREATE INDEX IX_posts_category_id ON dbo.posts(category_id);
GO
IF OBJECT_ID(N'dbo.FK_posts_users', N'F') IS NULL
    ALTER TABLE dbo.posts ADD CONSTRAINT FK_posts_users FOREIGN KEY(author_id) REFERENCES dbo.users(id);
GO
IF OBJECT_ID(N'dbo.FK_posts_categories', N'F') IS NULL
    ALTER TABLE dbo.posts ADD CONSTRAINT FK_posts_categories FOREIGN KEY(category_id) REFERENCES dbo.categories(id);
GO

IF OBJECT_ID(N'dbo.post_tags', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.post_tags (
        post_id INT NOT NULL,
        tag_id  INT NOT NULL,
        CONSTRAINT PK_post_tags PRIMARY KEY CLUSTERED (post_id, tag_id)
    );
END
GO
IF OBJECT_ID(N'dbo.FK_post_tags_posts', N'F') IS NULL
    ALTER TABLE dbo.post_tags ADD CONSTRAINT FK_post_tags_posts FOREIGN KEY(post_id) REFERENCES dbo.posts(id) ON DELETE CASCADE;
GO
IF OBJECT_ID(N'dbo.FK_post_tags_tags', N'F') IS NULL
    ALTER TABLE dbo.post_tags ADD CONSTRAINT FK_post_tags_tags FOREIGN KEY(tag_id) REFERENCES dbo.tags(id) ON DELETE CASCADE;
GO

IF OBJECT_ID(N'dbo.comments', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.comments (
        id            INT            IDENTITY(1,1) NOT NULL PRIMARY KEY,
        post_id       INT            NOT NULL,
        parent_id     INT            NULL,
        author_name   NVARCHAR(128)  NOT NULL,
        content       NVARCHAR(MAX)  NOT NULL,
        status        NVARCHAR(20)   NOT NULL CONSTRAINT DF_comments_status DEFAULT (N'approved'),
        reject_type   NVARCHAR(32)   NULL,
        reject_reason NVARCHAR(300)  NULL,
        created_at    DATETIME2(3)   NOT NULL
    );
END
GO
IF OBJECT_ID(N'dbo.FK_comments_posts', N'F') IS NULL
    ALTER TABLE dbo.comments ADD CONSTRAINT FK_comments_posts FOREIGN KEY(post_id) REFERENCES dbo.posts(id) ON DELETE CASCADE;
GO
IF OBJECT_ID(N'dbo.FK_comments_parent', N'F') IS NULL
    ALTER TABLE dbo.comments ADD CONSTRAINT FK_comments_parent FOREIGN KEY(parent_id) REFERENCES dbo.comments(id);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.comments') AND name = N'IX_comments_post_id')
    CREATE INDEX IX_comments_post_id ON dbo.comments(post_id);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.comments') AND name = N'IX_comments_parent_id')
    CREATE INDEX IX_comments_parent_id ON dbo.comments(parent_id);
GO

/* ==================== 互动与社交 ==================== */
IF OBJECT_ID(N'dbo.post_favorites', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.post_favorites (
        id         INT            IDENTITY(1,1) NOT NULL PRIMARY KEY,
        post_id    INT            NOT NULL,
        user_key   NVARCHAR(128)  NOT NULL,
        created_at DATETIME2(3)   NOT NULL
    );
END
GO
IF OBJECT_ID(N'dbo.FK_post_favorites_posts', N'F') IS NULL
    ALTER TABLE dbo.post_favorites ADD CONSTRAINT FK_post_favorites_posts FOREIGN KEY(post_id) REFERENCES dbo.posts(id) ON DELETE CASCADE;
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.post_favorites') AND name = N'UQ_post_favorites_post_user')
    CREATE UNIQUE INDEX UQ_post_favorites_post_user ON dbo.post_favorites(post_id, user_key);
GO

IF OBJECT_ID(N'dbo.post_likes', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.post_likes (
        id         INT            IDENTITY(1,1) NOT NULL PRIMARY KEY,
        post_id    INT            NOT NULL,
        user_key   NVARCHAR(128)  NOT NULL,
        created_at DATETIME2(3)   NOT NULL
    );
END
GO
IF OBJECT_ID(N'dbo.FK_post_likes_posts', N'F') IS NULL
    ALTER TABLE dbo.post_likes ADD CONSTRAINT FK_post_likes_posts FOREIGN KEY(post_id) REFERENCES dbo.posts(id) ON DELETE CASCADE;
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.post_likes') AND name = N'UQ_post_likes_post_user')
    CREATE UNIQUE INDEX UQ_post_likes_post_user ON dbo.post_likes(post_id, user_key);
GO

IF OBJECT_ID(N'dbo.post_shares', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.post_shares (
        id         INT            IDENTITY(1,1) NOT NULL PRIMARY KEY,
        post_id    INT            NOT NULL,
        channel    NVARCHAR(32)   NOT NULL CONSTRAINT DF_post_shares_channel DEFAULT (N'link'),
        user_key   NVARCHAR(128)  NULL,
        created_at DATETIME2(3)   NOT NULL
    );
END
GO
IF OBJECT_ID(N'dbo.FK_post_shares_posts', N'F') IS NULL
    ALTER TABLE dbo.post_shares ADD CONSTRAINT FK_post_shares_posts FOREIGN KEY(post_id) REFERENCES dbo.posts(id) ON DELETE CASCADE;
GO

IF OBJECT_ID(N'dbo.post_reports', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.post_reports (
        id         INT             IDENTITY(1,1) NOT NULL PRIMARY KEY,
        post_id    INT             NOT NULL,
        reason     NVARCHAR(64)    NOT NULL,
        detail     NVARCHAR(1000)  NULL,
        user_key   NVARCHAR(128)   NULL,
        reviewed   BIT             NOT NULL CONSTRAINT DF_post_reports_reviewed DEFAULT (0),
        created_at DATETIME2(3)    NOT NULL
    );
END
GO
IF OBJECT_ID(N'dbo.FK_post_reports_posts', N'F') IS NULL
    ALTER TABLE dbo.post_reports ADD CONSTRAINT FK_post_reports_posts FOREIGN KEY(post_id) REFERENCES dbo.posts(id) ON DELETE CASCADE;
GO

IF OBJECT_ID(N'dbo.post_view_events', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.post_view_events (
        id           INT            IDENTITY(1,1) NOT NULL PRIMARY KEY,
        post_id      INT            NOT NULL,
        user_key     NVARCHAR(128)  NOT NULL,
        duration_sec INT            NOT NULL CONSTRAINT DF_post_view_events_duration DEFAULT (0),
        completed    BIT            NOT NULL CONSTRAINT DF_post_view_events_completed DEFAULT (0),
        created_at   DATETIME2(3)   NOT NULL
    );
END
GO
IF OBJECT_ID(N'dbo.FK_post_view_events_posts', N'F') IS NULL
    ALTER TABLE dbo.post_view_events ADD CONSTRAINT FK_post_view_events_posts FOREIGN KEY(post_id) REFERENCES dbo.posts(id) ON DELETE CASCADE;
GO

IF OBJECT_ID(N'dbo.author_follows', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.author_follows (
        id         INT            IDENTITY(1,1) NOT NULL PRIMARY KEY,
        user_key   NVARCHAR(128)  NOT NULL,
        author_id  INT            NOT NULL,
        created_at DATETIME2(3)   NOT NULL
    );
END
GO
IF OBJECT_ID(N'dbo.FK_author_follows_users', N'F') IS NULL
    ALTER TABLE dbo.author_follows ADD CONSTRAINT FK_author_follows_users FOREIGN KEY(author_id) REFERENCES dbo.users(id) ON DELETE CASCADE;
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.author_follows') AND name = N'UQ_author_follows_user_author')
    CREATE UNIQUE INDEX UQ_author_follows_user_author ON dbo.author_follows(user_key, author_id);
GO

/* ==================== 专栏 ==================== */
IF OBJECT_ID(N'dbo.columns', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.columns (
        id              INT            IDENTITY(1,1) NOT NULL PRIMARY KEY,
        name            NVARCHAR(128)  NOT NULL,
        slug            NVARCHAR(128)  NOT NULL,
        description     NVARCHAR(500)  NULL,
        cover_image_url NVARCHAR(512)  NULL,
        is_public       BIT            NOT NULL CONSTRAINT DF_columns_is_public DEFAULT (1),
        author_id       INT            NULL,
        created_at      DATETIME2(3)   NOT NULL,
        updated_at      DATETIME2(3)   NOT NULL
    );
END
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.columns') AND name = N'UQ_columns_slug')
    CREATE UNIQUE INDEX UQ_columns_slug ON dbo.columns(slug);
GO
IF OBJECT_ID(N'dbo.FK_columns_users', N'F') IS NULL
    ALTER TABLE dbo.columns ADD CONSTRAINT FK_columns_users FOREIGN KEY(author_id) REFERENCES dbo.users(id) ON DELETE SET NULL;
GO

IF OBJECT_ID(N'dbo.column_posts', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.column_posts (
        column_id   INT NOT NULL,
        post_id     INT NOT NULL,
        sort_order  INT NOT NULL CONSTRAINT DF_column_posts_sort_order DEFAULT (0),
        CONSTRAINT PK_column_posts PRIMARY KEY CLUSTERED (column_id, post_id)
    );
END
GO
IF OBJECT_ID(N'dbo.FK_column_posts_columns', N'F') IS NULL
    ALTER TABLE dbo.column_posts ADD CONSTRAINT FK_column_posts_columns FOREIGN KEY(column_id) REFERENCES dbo.columns(id) ON DELETE CASCADE;
GO
IF OBJECT_ID(N'dbo.FK_column_posts_posts', N'F') IS NULL
    ALTER TABLE dbo.column_posts ADD CONSTRAINT FK_column_posts_posts FOREIGN KEY(post_id) REFERENCES dbo.posts(id) ON DELETE CASCADE;
GO

/* ==================== 运营 ==================== */
IF OBJECT_ID(N'dbo.feature_flags', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.feature_flags (
        id              INT            IDENTITY(1,1) NOT NULL PRIMARY KEY,
        code            NVARCHAR(64)   NOT NULL,
        name            NVARCHAR(128)  NOT NULL,
        enabled         BIT            NOT NULL CONSTRAINT DF_feature_flags_enabled DEFAULT (0),
        rollout_percent INT            NOT NULL CONSTRAINT DF_feature_flags_rollout_percent DEFAULT (0),
        created_at      DATETIME2(3)   NOT NULL
    );
END
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.feature_flags') AND name = N'UQ_feature_flags_code')
    CREATE UNIQUE INDEX UQ_feature_flags_code ON dbo.feature_flags(code);
GO

IF OBJECT_ID(N'dbo.sensitive_words', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.sensitive_words (
        id         INT            IDENTITY(1,1) NOT NULL PRIMARY KEY,
        word       NVARCHAR(64)   NOT NULL,
        enabled    BIT            NOT NULL CONSTRAINT DF_sensitive_words_enabled DEFAULT (1),
        created_at DATETIME2(3)   NOT NULL
    );
END
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.sensitive_words') AND name = N'UQ_sensitive_words_word')
    CREATE UNIQUE INDEX UQ_sensitive_words_word ON dbo.sensitive_words(word);
GO

IF OBJECT_ID(N'dbo.blacklist_words', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.blacklist_words (
        id         INT            IDENTITY(1,1) NOT NULL PRIMARY KEY,
        word       NVARCHAR(64)   NOT NULL,
        enabled    BIT            NOT NULL CONSTRAINT DF_blacklist_words_enabled DEFAULT (1),
        created_at DATETIME2(3)   NOT NULL
    );
END
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.blacklist_words') AND name = N'UQ_blacklist_words_word')
    CREATE UNIQUE INDEX UQ_blacklist_words_word ON dbo.blacklist_words(word);
GO

IF OBJECT_ID(N'dbo.search_synonyms', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.search_synonyms (
        id         INT            IDENTITY(1,1) NOT NULL PRIMARY KEY,
        src        NVARCHAR(64)   NOT NULL,
        dst        NVARCHAR(64)   NOT NULL,
        enabled    BIT            NOT NULL CONSTRAINT DF_search_synonyms_enabled DEFAULT (1),
        created_at DATETIME2(3)   NOT NULL
    );
END
GO

IF OBJECT_ID(N'dbo.search_hotwords', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.search_hotwords (
        id         INT             IDENTITY(1,1) NOT NULL PRIMARY KEY,
        keyword    NVARCHAR(128)   NOT NULL,
        cnt        INT             NOT NULL CONSTRAINT DF_search_hotwords_cnt DEFAULT (0),
        updated_at DATETIME2(3)    NOT NULL
    );
END
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.search_hotwords') AND name = N'UQ_search_hotwords_keyword')
    CREATE UNIQUE INDEX UQ_search_hotwords_keyword ON dbo.search_hotwords(keyword);
GO

/* ==================== RBAC ==================== */
IF OBJECT_ID(N'dbo.roles', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.roles (
        id         INT            IDENTITY(1,1) NOT NULL PRIMARY KEY,
        code       NVARCHAR(64)   NOT NULL,
        name       NVARCHAR(64)   NOT NULL,
        data_scope NVARCHAR(20)   NOT NULL CONSTRAINT DF_roles_data_scope DEFAULT (N'all'),
        is_active  BIT            NOT NULL CONSTRAINT DF_roles_is_active DEFAULT (1),
        created_at DATETIME2(3)   NOT NULL
    );
END
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.roles') AND name = N'UQ_roles_code')
    CREATE UNIQUE INDEX UQ_roles_code ON dbo.roles(code);
GO

IF OBJECT_ID(N'dbo.permissions', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.permissions (
        id         INT             IDENTITY(1,1) NOT NULL PRIMARY KEY,
        code       NVARCHAR(128)   NOT NULL,
        name       NVARCHAR(128)   NOT NULL,
        created_at DATETIME2(3)    NOT NULL
    );
END
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.permissions') AND name = N'UQ_permissions_code')
    CREATE UNIQUE INDEX UQ_permissions_code ON dbo.permissions(code);
GO

IF OBJECT_ID(N'dbo.menus', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.menus (
        id         INT             IDENTITY(1,1) NOT NULL PRIMARY KEY,
        code       NVARCHAR(128)   NOT NULL,
        name       NVARCHAR(64)    NOT NULL,
        route      NVARCHAR(256)   NOT NULL,
        icon       NVARCHAR(64)    NULL,
        order_no   INT             NOT NULL CONSTRAINT DF_menus_order_no DEFAULT (0),
        hidden     BIT             NOT NULL CONSTRAINT DF_menus_hidden DEFAULT (0),
        created_at DATETIME2(3)    NOT NULL
    );
END
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.menus') AND name = N'UQ_menus_code')
    CREATE UNIQUE INDEX UQ_menus_code ON dbo.menus(code);
GO

IF OBJECT_ID(N'dbo.user_roles', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.user_roles (
        id         INT            IDENTITY(1,1) NOT NULL PRIMARY KEY,
        user_id    INT            NOT NULL,
        role_id    INT            NOT NULL,
        created_at DATETIME2(3)   NOT NULL
    );
END
GO
IF OBJECT_ID(N'dbo.FK_user_roles_users', N'F') IS NULL
    ALTER TABLE dbo.user_roles ADD CONSTRAINT FK_user_roles_users FOREIGN KEY(user_id) REFERENCES dbo.users(id) ON DELETE CASCADE;
GO
IF OBJECT_ID(N'dbo.FK_user_roles_roles', N'F') IS NULL
    ALTER TABLE dbo.user_roles ADD CONSTRAINT FK_user_roles_roles FOREIGN KEY(role_id) REFERENCES dbo.roles(id) ON DELETE CASCADE;
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.user_roles') AND name = N'UQ_user_roles_user_role')
    CREATE UNIQUE INDEX UQ_user_roles_user_role ON dbo.user_roles(user_id, role_id);
GO

IF OBJECT_ID(N'dbo.role_permissions', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.role_permissions (
        id            INT            IDENTITY(1,1) NOT NULL PRIMARY KEY,
        role_id       INT            NOT NULL,
        permission_id INT            NOT NULL,
        created_at    DATETIME2(3)   NOT NULL
    );
END
GO
IF OBJECT_ID(N'dbo.FK_role_permissions_roles', N'F') IS NULL
    ALTER TABLE dbo.role_permissions ADD CONSTRAINT FK_role_permissions_roles FOREIGN KEY(role_id) REFERENCES dbo.roles(id) ON DELETE CASCADE;
GO
IF OBJECT_ID(N'dbo.FK_role_permissions_permissions', N'F') IS NULL
    ALTER TABLE dbo.role_permissions ADD CONSTRAINT FK_role_permissions_permissions FOREIGN KEY(permission_id) REFERENCES dbo.permissions(id) ON DELETE CASCADE;
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.role_permissions') AND name = N'UQ_role_permissions')
    CREATE UNIQUE INDEX UQ_role_permissions ON dbo.role_permissions(role_id, permission_id);
GO

IF OBJECT_ID(N'dbo.role_menus', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.role_menus (
        id         INT            IDENTITY(1,1) NOT NULL PRIMARY KEY,
        role_id    INT            NOT NULL,
        menu_id    INT            NOT NULL,
        created_at DATETIME2(3)   NOT NULL
    );
END
GO
IF OBJECT_ID(N'dbo.FK_role_menus_roles', N'F') IS NULL
    ALTER TABLE dbo.role_menus ADD CONSTRAINT FK_role_menus_roles FOREIGN KEY(role_id) REFERENCES dbo.roles(id) ON DELETE CASCADE;
GO
IF OBJECT_ID(N'dbo.FK_role_menus_menus', N'F') IS NULL
    ALTER TABLE dbo.role_menus ADD CONSTRAINT FK_role_menus_menus FOREIGN KEY(menu_id) REFERENCES dbo.menus(id) ON DELETE CASCADE;
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.role_menus') AND name = N'UQ_role_menus')
    CREATE UNIQUE INDEX UQ_role_menus ON dbo.role_menus(role_id, menu_id);
GO

IF OBJECT_ID(N'dbo.audit_logs', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.audit_logs (
        id            INT             IDENTITY(1,1) NOT NULL PRIMARY KEY,
        actor_user_id INT             NULL,
        action        NVARCHAR(128)   NOT NULL,
        target_type   NVARCHAR(64)    NOT NULL,
        target_id     NVARCHAR(64)    NOT NULL,
        detail        NVARCHAR(2000)  NULL,
        created_at    DATETIME2(3)    NOT NULL
    );
END
GO
IF OBJECT_ID(N'dbo.FK_audit_logs_users', N'F') IS NULL
    ALTER TABLE dbo.audit_logs ADD CONSTRAINT FK_audit_logs_users FOREIGN KEY(actor_user_id) REFERENCES dbo.users(id) ON DELETE SET NULL;
GO

/* ==================== 工作流 ==================== */
IF OBJECT_ID(N'dbo.workflow_reason_templates', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.workflow_reason_templates (
        id         INT            IDENTITY(1,1) NOT NULL PRIMARY KEY,
        name       NVARCHAR(64)   NOT NULL,
        content    NVARCHAR(500)  NOT NULL,
        enabled    BIT            NOT NULL CONSTRAINT DF_workflow_reason_templates_enabled DEFAULT (1),
        created_at DATETIME2(3)   NOT NULL
    );
END
GO

IF OBJECT_ID(N'dbo.workflow_audits', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.workflow_audits (
        id          INT             IDENTITY(1,1) NOT NULL PRIMARY KEY,
        task_type   NVARCHAR(20)    NOT NULL,
        biz_id      INT             NOT NULL,
        operator_id INT             NOT NULL,
        action      NVARCHAR(30)    NOT NULL,
        from_status NVARCHAR(30)    NULL,
        to_status   NVARCHAR(30)    NULL,
        remark      NVARCHAR(MAX)   NULL,
        created_at  DATETIME2(3)    NOT NULL
    );
END
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.workflow_audits') AND name = N'IX_workflow_audits_task_type')
    CREATE INDEX IX_workflow_audits_task_type ON dbo.workflow_audits(task_type);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.workflow_audits') AND name = N'IX_workflow_audits_biz_id')
    CREATE INDEX IX_workflow_audits_biz_id ON dbo.workflow_audits(biz_id);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID(N'dbo.workflow_audits') AND name = N'IX_workflow_audits_created_at')
    CREATE INDEX IX_workflow_audits_created_at ON dbo.workflow_audits(created_at);
GO

/* ==================== 字段说明（MS_Description） ==================== */
SET NOCOUNT ON;

DECLARE @desc TABLE (
    table_name  SYSNAME        NOT NULL,
    column_name SYSNAME        NULL,
    [value]     NVARCHAR(1000) NOT NULL
);

INSERT INTO @desc(table_name, column_name, [value]) VALUES
(N'users', NULL, N'后台登录用户'),
(N'categories', NULL, N'文章分类'),
(N'tags', NULL, N'文章标签'),
(N'posts', NULL, N'文章主表'),
(N'post_tags', NULL, N'文章与标签关联'),
(N'comments', NULL, N'评论表'),
(N'post_favorites', NULL, N'收藏记录'),
(N'post_likes', NULL, N'点赞记录'),
(N'post_shares', NULL, N'分享记录'),
(N'post_reports', NULL, N'举报记录'),
(N'post_view_events', NULL, N'浏览事件'),
(N'author_follows', NULL, N'作者关注关系'),
(N'columns', NULL, N'专栏主表'),
(N'column_posts', NULL, N'专栏文章关联'),
(N'feature_flags', NULL, N'功能开关'),
(N'sensitive_words', NULL, N'敏感词'),
(N'blacklist_words', NULL, N'黑名单词'),
(N'search_synonyms', NULL, N'搜索同义词'),
(N'search_hotwords', NULL, N'搜索热词'),
(N'roles', NULL, N'角色'),
(N'permissions', NULL, N'权限点'),
(N'menus', NULL, N'后台菜单'),
(N'user_roles', NULL, N'用户角色关联'),
(N'role_permissions', NULL, N'角色权限关联'),
(N'role_menus', NULL, N'角色菜单关联'),
(N'audit_logs', NULL, N'后台审计日志'),
(N'workflow_reason_templates', NULL, N'流程原因模板'),
(N'workflow_audits', NULL, N'流程审计日志');

DECLARE @t SYSNAME, @c SYSNAME, @v NVARCHAR(1000);
DECLARE cur_desc CURSOR LOCAL FAST_FORWARD FOR
    SELECT table_name, column_name, [value] FROM @desc;

OPEN cur_desc;
FETCH NEXT FROM cur_desc INTO @t, @c, @v;
WHILE @@FETCH_STATUS = 0
BEGIN
    IF OBJECT_ID(N'dbo.' + @t, N'U') IS NOT NULL
    BEGIN
        IF @c IS NULL
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM sys.extended_properties ep
                WHERE ep.major_id = OBJECT_ID(N'dbo.' + @t)
                  AND ep.minor_id = 0
                  AND ep.name = N'MS_Description'
            )
                EXEC sys.sp_updateextendedproperty
                    @name = N'MS_Description', @value = @v,
                    @level0type = N'SCHEMA', @level0name = N'dbo',
                    @level1type = N'TABLE',  @level1name = @t;
            ELSE
                EXEC sys.sp_addextendedproperty
                    @name = N'MS_Description', @value = @v,
                    @level0type = N'SCHEMA', @level0name = N'dbo',
                    @level1type = N'TABLE',  @level1name = @t;
        END
    END
    FETCH NEXT FROM cur_desc INTO @t, @c, @v;
END

CLOSE cur_desc;
DEALLOCATE cur_desc;
GO

/* 为所有字段补齐注释：先用业务字典，再用“字段名”兜底，确保全字段都有说明 */
DECLARE @col_desc TABLE (
    table_name  SYSNAME        NOT NULL,
    column_name SYSNAME        NOT NULL,
    [value]     NVARCHAR(1000) NOT NULL
);

INSERT INTO @col_desc(table_name, column_name, [value]) VALUES
(N'users', N'id', N'主键ID'),
(N'users', N'username', N'用户名（唯一）'),
(N'users', N'hashed_password', N'密码哈希'),
(N'users', N'is_active', N'是否启用'),
(N'posts', N'review_status', N'审核状态：draft/pending/approved/rejected/offline'),
(N'posts', N'is_pinned', N'是否置顶'),
(N'posts', N'is_featured', N'是否精选'),
(N'comments', N'parent_id', N'父评论ID'),
(N'columns', N'is_public', N'是否公开'),
(N'column_posts', N'sort_order', N'专栏内排序（升序）'),
(N'feature_flags', N'rollout_percent', N'灰度比例（0-100）'),
(N'roles', N'data_scope', N'数据权限范围'),
(N'menus', N'order_no', N'菜单排序号'),
(N'workflow_audits', N'biz_id', N'业务对象ID'),
(N'workflow_audits', N'operator_id', N'操作人ID');

DECLARE @ot SYSNAME, @oc SYSNAME, @ov NVARCHAR(1000);
DECLARE cur_col CURSOR LOCAL FAST_FORWARD FOR
    SELECT table_name, column_name, [value] FROM @col_desc;

OPEN cur_col;
FETCH NEXT FROM cur_col INTO @ot, @oc, @ov;
WHILE @@FETCH_STATUS = 0
BEGIN
    IF OBJECT_ID(N'dbo.' + @ot, N'U') IS NOT NULL
       AND COL_LENGTH(N'dbo.' + @ot, @oc) IS NOT NULL
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM sys.extended_properties ep
            JOIN sys.columns c ON c.object_id = ep.major_id AND c.column_id = ep.minor_id
            WHERE ep.major_id = OBJECT_ID(N'dbo.' + @ot)
              AND c.name = @oc
              AND ep.name = N'MS_Description'
        )
            EXEC sys.sp_updateextendedproperty
                @name = N'MS_Description', @value = @ov,
                @level0type = N'SCHEMA', @level0name = N'dbo',
                @level1type = N'TABLE',  @level1name = @ot,
                @level2type = N'COLUMN', @level2name = @oc;
        ELSE
            EXEC sys.sp_addextendedproperty
                @name = N'MS_Description', @value = @ov,
                @level0type = N'SCHEMA', @level0name = N'dbo',
                @level1type = N'TABLE',  @level1name = @ot,
                @level2type = N'COLUMN', @level2name = @oc;
    END
    FETCH NEXT FROM cur_col INTO @ot, @oc, @ov;
END

CLOSE cur_col;
DEALLOCATE cur_col;
GO

/* 对未写业务字典的字段，自动兜底注释为“字段：<column_name>” */
DECLARE @tt SYSNAME, @cc SYSNAME, @auto NVARCHAR(1000);
DECLARE cur_auto CURSOR LOCAL FAST_FORWARD FOR
SELECT t.name, c.name
FROM sys.tables t
JOIN sys.columns c ON c.object_id = t.object_id
LEFT JOIN sys.extended_properties ep
  ON ep.major_id = c.object_id
 AND ep.minor_id = c.column_id
 AND ep.name = N'MS_Description'
WHERE t.schema_id = SCHEMA_ID(N'dbo')
  AND ep.value IS NULL;

OPEN cur_auto;
FETCH NEXT FROM cur_auto INTO @tt, @cc;
WHILE @@FETCH_STATUS = 0
BEGIN
    SET @auto = N'字段：' + @cc;
    EXEC sys.sp_addextendedproperty
        @name = N'MS_Description', @value = @auto,
        @level0type = N'SCHEMA', @level0name = N'dbo',
        @level1type = N'TABLE',  @level1name = @tt,
        @level2type = N'COLUMN', @level2name = @cc;
    FETCH NEXT FROM cur_auto INTO @tt, @cc;
END

CLOSE cur_auto;
DEALLOCATE cur_auto;
GO

/* 注释覆盖检查：若返回空结果，表示所有字段均有注释 */
;WITH all_cols AS (
    SELECT
        t.name AS table_name,
        c.name AS column_name,
        ep.value AS col_desc
    FROM sys.tables t
    JOIN sys.columns c ON c.object_id = t.object_id
    LEFT JOIN sys.extended_properties ep
      ON ep.major_id = c.object_id
     AND ep.minor_id = c.column_id
     AND ep.name = N'MS_Description'
    WHERE t.schema_id = SCHEMA_ID(N'dbo')
)
SELECT table_name, column_name
FROM all_cols
WHERE col_desc IS NULL
ORDER BY table_name, column_name;
GO

PRINT N'BlogDB 全量表结构与字段说明脚本执行完成。';
GO

