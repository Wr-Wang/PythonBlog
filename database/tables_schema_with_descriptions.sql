/*
  BlogDB 全量表结构脚本（SQL Server）
  ==================================
  用途：
  1) 新环境一键建表；
  2) 老环境增量补齐缺失列/索引；
  3) 与 backend/app/models 当前结构保持一致。

  使用顺序：
  - 先执行 database/init.sql
  - 再执行本文件
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

/* ==================== posts ==================== */

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

/* 老库补列（posts） */
IF COL_LENGTH(N'dbo.posts', N'review_status') IS NULL
    ALTER TABLE dbo.posts ADD review_status NVARCHAR(20) NOT NULL CONSTRAINT DF_posts_review_status_compat DEFAULT (N'draft');
GO
IF COL_LENGTH(N'dbo.posts', N'favorite_count') IS NULL
    ALTER TABLE dbo.posts ADD favorite_count INT NOT NULL CONSTRAINT DF_posts_favorite_count_compat DEFAULT (0);
GO
IF COL_LENGTH(N'dbo.posts', N'like_count') IS NULL
    ALTER TABLE dbo.posts ADD like_count INT NOT NULL CONSTRAINT DF_posts_like_count_compat DEFAULT (0);
GO
IF COL_LENGTH(N'dbo.posts', N'view_count') IS NULL
    ALTER TABLE dbo.posts ADD view_count INT NOT NULL CONSTRAINT DF_posts_view_count_compat DEFAULT (0);
GO
IF COL_LENGTH(N'dbo.posts', N'share_count') IS NULL
    ALTER TABLE dbo.posts ADD share_count INT NOT NULL CONSTRAINT DF_posts_share_count_compat DEFAULT (0);
GO
IF COL_LENGTH(N'dbo.posts', N'rank_level') IS NULL
    ALTER TABLE dbo.posts ADD rank_level INT NOT NULL CONSTRAINT DF_posts_rank_level_compat DEFAULT (1);
GO
IF COL_LENGTH(N'dbo.posts', N'weight') IS NULL
    ALTER TABLE dbo.posts ADD weight INT NOT NULL CONSTRAINT DF_posts_weight_compat DEFAULT (0);
GO
IF COL_LENGTH(N'dbo.posts', N'hot_score') IS NULL
    ALTER TABLE dbo.posts ADD hot_score INT NOT NULL CONSTRAINT DF_posts_hot_score_compat DEFAULT (0);
GO
IF COL_LENGTH(N'dbo.posts', N'is_featured') IS NULL
    ALTER TABLE dbo.posts ADD is_featured BIT NOT NULL CONSTRAINT DF_posts_is_featured_compat DEFAULT (0);
GO
IF COL_LENGTH(N'dbo.posts', N'is_pinned') IS NULL
    ALTER TABLE dbo.posts ADD is_pinned BIT NOT NULL CONSTRAINT DF_posts_is_pinned_compat DEFAULT (0);
GO
IF COL_LENGTH(N'dbo.posts', N'published_at') IS NULL
    ALTER TABLE dbo.posts ADD published_at DATETIME2(3) NULL;
GO
IF COL_LENGTH(N'dbo.posts', N'offline_at') IS NULL
    ALTER TABLE dbo.posts ADD offline_at DATETIME2(3) NULL;
GO
IF COL_LENGTH(N'dbo.posts', N'content_type') IS NULL
    ALTER TABLE dbo.posts ADD content_type NVARCHAR(20) NULL;
GO
IF COL_LENGTH(N'dbo.posts', N'source_url') IS NULL
    ALTER TABLE dbo.posts ADD source_url NVARCHAR(512) NULL;
GO

/* ==================== post_tags ==================== */
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

/* ==================== comments ==================== */
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

IF COL_LENGTH(N'dbo.comments', N'reject_type') IS NULL
    ALTER TABLE dbo.comments ADD reject_type NVARCHAR(32) NULL;
GO
IF COL_LENGTH(N'dbo.comments', N'reject_reason') IS NULL
    ALTER TABLE dbo.comments ADD reject_reason NVARCHAR(300) NULL;
GO

/* ==================== 互动表 ==================== */
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

/* ==================== 运营配置表 ==================== */
IF OBJECT_ID(N'dbo.feature_flags', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.feature_flags (
        id             INT            IDENTITY(1,1) NOT NULL PRIMARY KEY,
        code           NVARCHAR(64)   NOT NULL,
        name           NVARCHAR(128)  NOT NULL,
        enabled        BIT            NOT NULL CONSTRAINT DF_feature_flags_enabled DEFAULT (0),
        rollout_percent INT           NOT NULL CONSTRAINT DF_feature_flags_rollout_percent DEFAULT (0),
        created_at     DATETIME2(3)   NOT NULL
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
IF COL_LENGTH(N'dbo.roles', N'data_scope') IS NULL
    ALTER TABLE dbo.roles ADD data_scope NVARCHAR(20) NOT NULL CONSTRAINT DF_roles_data_scope_compat DEFAULT (N'all');
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
-- users
(N'users', NULL, N'后台登录用户表'),
(N'users', N'id', N'主键ID'),
(N'users', N'username', N'用户名，唯一'),
(N'users', N'hashed_password', N'密码哈希'),
(N'users', N'is_active', N'是否启用'),
(N'users', N'created_at', N'创建时间'),
-- categories
(N'categories', NULL, N'文章分类表'),
(N'categories', N'id', N'主键ID'),
(N'categories', N'name', N'分类名称'),
(N'categories', N'slug', N'分类唯一标识'),
(N'categories', N'created_at', N'创建时间'),
(N'categories', N'updated_at', N'更新时间'),
-- tags
(N'tags', NULL, N'文章标签表'),
(N'tags', N'id', N'主键ID'),
(N'tags', N'name', N'标签名称'),
(N'tags', N'slug', N'标签唯一标识'),
(N'tags', N'created_at', N'创建时间'),
-- posts
(N'posts', NULL, N'文章主表'),
(N'posts', N'id', N'主键ID'),
(N'posts', N'title', N'文章标题'),
(N'posts', N'slug', N'文章唯一标识'),
(N'posts', N'excerpt', N'文章摘要'),
(N'posts', N'content', N'文章正文'),
(N'posts', N'published', N'是否发布'),
(N'posts', N'review_status', N'审核状态'),
(N'posts', N'cover_image_url', N'封面图地址'),
(N'posts', N'favorite_count', N'收藏数'),
(N'posts', N'like_count', N'点赞数'),
(N'posts', N'view_count', N'浏览量'),
(N'posts', N'share_count', N'分享数'),
(N'posts', N'rank_level', N'排序等级'),
(N'posts', N'weight', N'运营权重'),
(N'posts', N'hot_score', N'热度分'),
(N'posts', N'is_featured', N'是否精选'),
(N'posts', N'is_pinned', N'是否置顶'),
(N'posts', N'published_at', N'发布时间'),
(N'posts', N'offline_at', N'下线时间'),
(N'posts', N'content_type', N'内容类型'),
(N'posts', N'source_url', N'来源链接'),
(N'posts', N'created_at', N'创建时间'),
(N'posts', N'updated_at', N'更新时间'),
(N'posts', N'author_id', N'作者用户ID'),
(N'posts', N'category_id', N'分类ID'),
-- post_tags
(N'post_tags', NULL, N'文章标签关联表'),
(N'post_tags', N'post_id', N'文章ID'),
(N'post_tags', N'tag_id', N'标签ID'),
-- comments
(N'comments', NULL, N'评论表'),
(N'comments', N'id', N'主键ID'),
(N'comments', N'post_id', N'所属文章ID'),
(N'comments', N'parent_id', N'父评论ID'),
(N'comments', N'author_name', N'评论者名称'),
(N'comments', N'content', N'评论内容'),
(N'comments', N'status', N'审核状态'),
(N'comments', N'reject_type', N'拒绝类型'),
(N'comments', N'reject_reason', N'拒绝原因'),
(N'comments', N'created_at', N'创建时间'),
-- interactions
(N'post_favorites', NULL, N'文章收藏关系'),
(N'post_favorites', N'id', N'主键ID'),
(N'post_favorites', N'post_id', N'文章ID'),
(N'post_favorites', N'user_key', N'用户标识'),
(N'post_favorites', N'created_at', N'创建时间'),
(N'post_likes', NULL, N'文章点赞关系'),
(N'post_likes', N'id', N'主键ID'),
(N'post_likes', N'post_id', N'文章ID'),
(N'post_likes', N'user_key', N'用户标识'),
(N'post_likes', N'created_at', N'创建时间'),
(N'post_shares', NULL, N'文章分享记录'),
(N'post_shares', N'id', N'主键ID'),
(N'post_shares', N'post_id', N'文章ID'),
(N'post_shares', N'channel', N'分享渠道'),
(N'post_shares', N'user_key', N'用户标识'),
(N'post_shares', N'created_at', N'创建时间'),
(N'post_reports', NULL, N'文章举报记录'),
(N'post_reports', N'id', N'主键ID'),
(N'post_reports', N'post_id', N'文章ID'),
(N'post_reports', N'reason', N'举报原因'),
(N'post_reports', N'detail', N'举报详情'),
(N'post_reports', N'user_key', N'用户标识'),
(N'post_reports', N'reviewed', N'是否已处理'),
(N'post_reports', N'created_at', N'创建时间'),
(N'post_view_events', NULL, N'文章浏览事件明细'),
(N'post_view_events', N'id', N'主键ID'),
(N'post_view_events', N'post_id', N'文章ID'),
(N'post_view_events', N'user_key', N'用户标识'),
(N'post_view_events', N'duration_sec', N'停留秒数'),
(N'post_view_events', N'completed', N'是否读完'),
(N'post_view_events', N'created_at', N'创建时间'),
-- ops
(N'feature_flags', NULL, N'功能开关表'),
(N'feature_flags', N'id', N'主键ID'),
(N'feature_flags', N'code', N'开关编码'),
(N'feature_flags', N'name', N'开关名称'),
(N'feature_flags', N'enabled', N'是否启用'),
(N'feature_flags', N'rollout_percent', N'灰度百分比'),
(N'feature_flags', N'created_at', N'创建时间'),
(N'sensitive_words', NULL, N'敏感词表'),
(N'sensitive_words', N'id', N'主键ID'),
(N'sensitive_words', N'word', N'敏感词'),
(N'sensitive_words', N'enabled', N'是否启用'),
(N'sensitive_words', N'created_at', N'创建时间'),
(N'blacklist_words', NULL, N'黑名单词表'),
(N'blacklist_words', N'id', N'主键ID'),
(N'blacklist_words', N'word', N'黑名单词'),
(N'blacklist_words', N'enabled', N'是否启用'),
(N'blacklist_words', N'created_at', N'创建时间'),
(N'search_synonyms', NULL, N'搜索同义词表'),
(N'search_synonyms', N'id', N'主键ID'),
(N'search_synonyms', N'src', N'原词'),
(N'search_synonyms', N'dst', N'同义词'),
(N'search_synonyms', N'enabled', N'是否启用'),
(N'search_synonyms', N'created_at', N'创建时间'),
(N'search_hotwords', NULL, N'搜索热词统计表'),
(N'search_hotwords', N'id', N'主键ID'),
(N'search_hotwords', N'keyword', N'关键词'),
(N'search_hotwords', N'cnt', N'热度计数'),
(N'search_hotwords', N'updated_at', N'更新时间'),
-- rbac
(N'roles', NULL, N'角色表'),
(N'roles', N'id', N'主键ID'),
(N'roles', N'code', N'角色编码'),
(N'roles', N'name', N'角色名称'),
(N'roles', N'data_scope', N'数据权限范围'),
(N'roles', N'is_active', N'是否启用'),
(N'roles', N'created_at', N'创建时间'),
(N'permissions', NULL, N'权限点表'),
(N'permissions', N'id', N'主键ID'),
(N'permissions', N'code', N'权限编码'),
(N'permissions', N'name', N'权限名称'),
(N'permissions', N'created_at', N'创建时间'),
(N'menus', NULL, N'后台菜单表'),
(N'menus', N'id', N'主键ID'),
(N'menus', N'code', N'菜单编码'),
(N'menus', N'name', N'菜单名称'),
(N'menus', N'route', N'菜单路由'),
(N'menus', N'icon', N'图标'),
(N'menus', N'order_no', N'排序号'),
(N'menus', N'hidden', N'是否隐藏'),
(N'menus', N'created_at', N'创建时间'),
(N'user_roles', NULL, N'用户角色关联表'),
(N'user_roles', N'id', N'主键ID'),
(N'user_roles', N'user_id', N'用户ID'),
(N'user_roles', N'role_id', N'角色ID'),
(N'user_roles', N'created_at', N'创建时间'),
(N'role_permissions', NULL, N'角色权限关联表'),
(N'role_permissions', N'id', N'主键ID'),
(N'role_permissions', N'role_id', N'角色ID'),
(N'role_permissions', N'permission_id', N'权限ID'),
(N'role_permissions', N'created_at', N'创建时间'),
(N'role_menus', NULL, N'角色菜单关联表'),
(N'role_menus', N'id', N'主键ID'),
(N'role_menus', N'role_id', N'角色ID'),
(N'role_menus', N'menu_id', N'菜单ID'),
(N'role_menus', N'created_at', N'创建时间'),
(N'audit_logs', NULL, N'后台审计日志表'),
(N'audit_logs', N'id', N'主键ID'),
(N'audit_logs', N'actor_user_id', N'操作人ID'),
(N'audit_logs', N'action', N'动作'),
(N'audit_logs', N'target_type', N'目标类型'),
(N'audit_logs', N'target_id', N'目标ID'),
(N'audit_logs', N'detail', N'明细'),
(N'audit_logs', N'created_at', N'创建时间'),
-- workflow
(N'workflow_reason_templates', NULL, N'流程原因模板表'),
(N'workflow_reason_templates', N'id', N'主键ID'),
(N'workflow_reason_templates', N'name', N'模板名称'),
(N'workflow_reason_templates', N'content', N'模板内容'),
(N'workflow_reason_templates', N'enabled', N'是否启用'),
(N'workflow_reason_templates', N'created_at', N'创建时间'),
(N'workflow_audits', NULL, N'流程审计表'),
(N'workflow_audits', N'id', N'主键ID'),
(N'workflow_audits', N'task_type', N'任务类型'),
(N'workflow_audits', N'biz_id', N'业务ID'),
(N'workflow_audits', N'operator_id', N'操作人ID'),
(N'workflow_audits', N'action', N'动作'),
(N'workflow_audits', N'from_status', N'原状态'),
(N'workflow_audits', N'to_status', N'目标状态'),
(N'workflow_audits', N'remark', N'备注'),
(N'workflow_audits', N'created_at', N'创建时间');

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
        ELSE IF COL_LENGTH(N'dbo.' + @t, @c) IS NOT NULL
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM sys.extended_properties ep
                JOIN sys.columns c ON c.object_id = ep.major_id AND c.column_id = ep.minor_id
                WHERE ep.major_id = OBJECT_ID(N'dbo.' + @t)
                  AND c.name = @c
                  AND ep.name = N'MS_Description'
            )
                EXEC sys.sp_updateextendedproperty
                    @name = N'MS_Description', @value = @v,
                    @level0type = N'SCHEMA', @level0name = N'dbo',
                    @level1type = N'TABLE',  @level1name = @t,
                    @level2type = N'COLUMN', @level2name = @c;
            ELSE
                EXEC sys.sp_addextendedproperty
                    @name = N'MS_Description', @value = @v,
                    @level0type = N'SCHEMA', @level0name = N'dbo',
                    @level1type = N'TABLE',  @level1name = @t,
                    @level2type = N'COLUMN', @level2name = @c;
        END
    END

    FETCH NEXT FROM cur_desc INTO @t, @c, @v;
END

CLOSE cur_desc;
DEALLOCATE cur_desc;
GO

PRINT N'BlogDB 全量结构脚本执行完成（含增量补齐与字段说明）。';
GO
